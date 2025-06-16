from datetime import datetime, timezone
import discord
from discord.ext import commands
from discord import app_commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select
from ...db.session import AsyncSessionLocal
from ...models.mail import MailConnection
from ...config import settings
import httpx
import pytz

def to_utc(dt):
    """日時をUTCのタイムゾーン付きに変換"""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

class MailSchedulerCog(commands.Cog):
    """メール取得の定期実行を管理するCog"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.scheduler = AsyncIOScheduler()
        # 30分ごとにメール取得を実行
        self.scheduler.add_job(
            self.fetch_all_mails,
            IntervalTrigger(minutes=30),
            name="fetch_all_mails",
            replace_existing=True,
        )
        self.scheduler.start()

    @app_commands.command(name="mail-notify", description="メール通知のテストを実行します")
    @app_commands.describe(
        limit="取得するメールの数（1-20）",
        skip_notification="通知を送信せずに取得のみ行う場合はTrue"
    )
    async def test_mail_notify(
        self,
        interaction: discord.Interaction,
        limit: app_commands.Range[int, 1, 20] = 5,
        skip_notification: bool = False
    ) -> None:
        """メール通知のテストを実行するコマンド"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            async with AsyncSessionLocal() as session:
                # ユーザーの連携情報を取得
                result = await session.execute(
                    select(MailConnection).where(
                        MailConnection.guild_id == str(interaction.guild_id),
                        MailConnection.user_id == str(interaction.user.id),
                    )
                )
                connection = result.scalar_one_or_none()
                
                if not connection:
                    await interaction.followup.send(
                        "メール連携が設定されていません。`/mail-connect`で設定してください。",
                        ephemeral=True
                    )
                    return

                print(f"[DEBUG] メール通知テスト開始 - ユーザー: {connection.email}")

                # メール取得・通知テスト
                try:
                    mails = await self.fetch_user_mails(
                        connection,
                        session,
                        limit=limit,
                        skip_notification=skip_notification
                    )
                    
                    # 取得結果のサマリーを送信
                    summary = f"📧 メール通知テストが完了しました。\n"
                    summary += f"**取得したメール数:** {len(mails)}件\n"
                    
                    if not skip_notification and mails:
                        summary += "**結果:** チャンネルに通知を送信しました。"
                    elif skip_notification and mails:
                        # 通知をスキップした場合は、件名一覧を表示
                        summary += "\n**取得したメール:**\n"
                        for i, mail in enumerate(mails[:3], 1):  # 最初の3件のみ表示
                            subject = mail.get("subject", "件名なし")[:50]
                            sender = mail.get("from", {}).get("emailAddress", {}).get("address", "不明")
                            summary += f"`{i}.` {subject}\n    📧 From: {sender}\n"
                        if len(mails) > 3:
                            summary += f"...他 {len(mails) - 3} 件"
                    else:
                        summary += "**結果:** 新着メールはありませんでした。"
                    
                    await interaction.followup.send(summary, ephemeral=True)
                    
                except Exception as e:
                    print(f"[ERROR] メール通知テストでエラー: {e}")
                    await interaction.followup.send(
                        f"❌ メール通知テストでエラーが発生しました:\n```{str(e)}```",
                        ephemeral=True
                    )
        except Exception as e:
            print(f"[ERROR] 全体エラー: {e}")
            await interaction.followup.send(
                f"❌ エラーが発生しました:\n```{str(e)}```",
                ephemeral=True
            )

    async def fetch_all_mails(self):
        """全ユーザーのメールを取得（定期実行用）"""
        print("[DEBUG] 定期メール取得を開始")
        try:
            async with AsyncSessionLocal() as session:
                # 有効な連携を全て取得
                current_time = datetime.now(timezone.utc).replace(tzinfo=None)
                result = await session.execute(
                    select(MailConnection).where(
                        MailConnection.token_expires_at > current_time
                    )
                )
                connections = result.scalars().all()
                print(f"[DEBUG] 有効な連携数: {len(connections)}")

                for connection in connections:
                    try:
                        print(f"[DEBUG] メール取得開始: {connection.email}")
                        await self.fetch_user_mails(connection, session, limit=5)
                    except Exception as e:
                        print(f"[ERROR] ユーザー {connection.user_id} のメール取得に失敗: {e}")
                        continue

        except Exception as e:
            print(f"[ERROR] メール一括取得処理でエラー発生: {e}")

    async def fetch_user_mails(
        self,
        connection: MailConnection,
        session,
        limit: int = 5,
        skip_notification: bool = False
    ):
        """個別ユーザーのメール取得処理"""
        from ..cogs.mail import ensure_valid_access_token

        try:
            # トークンの有効性確認と更新
            access_token = await ensure_valid_access_token(connection, session)
            
            # Microsoft Graph APIでメール取得
            url = "https://graph.microsoft.com/v1.0/me/messages"
            headers = {"Authorization": f"Bearer {access_token}"}
            params = {
                "$top": min(20, limit),  # 最大20件まで
                "$orderby": "receivedDateTime desc",
                "$select": "subject,from,receivedDateTime,id"
            }

            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, params=params)
                
                if response.status_code != 200:
                    print(f"[ERROR] メール取得APIでエラー: {response.status_code} - {response.text}")
                    return []

                mails = response.json().get("value", [])
                print(f"[DEBUG] 取得したメール数: {len(mails)}")
                
                if not skip_notification and mails:
                    # 取得したメールをDiscordに通知
                    guild = self.bot.get_guild(int(connection.guild_id))
                    if not guild:
                        print(f"[ERROR] Guild not found: {connection.guild_id}")
                        return mails

                    # 最新の3件のみ通知
                    for mail in mails[:3]:
                        await self.notify_mail(guild, connection, mail)

            # 最終チェック時刻を更新
            connection.last_checked_at = datetime.now(timezone.utc).replace(tzinfo=None)
            await session.commit()

            return mails

        except Exception as e:
            print(f"[ERROR] メール取得処理でエラー発生: {e}")
            raise

    async def notify_mail(self, guild: discord.Guild, connection: MailConnection, mail: dict):
        """メールをDiscordに通知"""
        try:
            # システムチャンネルに通知
            channel = guild.system_channel
            if not channel:
                print(f"[ERROR] System channel not found in guild: {guild.id}")
                return

            # Embedの作成
            subject = mail.get("subject", "件名なし")
            embed = discord.Embed(
                title=f"📧 {subject}",
                color=discord.Color.blue(),
                timestamp=datetime.fromisoformat(mail["receivedDateTime"].replace("Z", "+00:00"))
            )
            
            sender = mail.get("from", {}).get("emailAddress", {})
            sender_name = sender.get("name", "不明")
            sender_address = sender.get("address", "不明なアドレス")
            
            embed.add_field(
                name="送信者",
                value=f"{sender_name} ({sender_address})",
                inline=False
            )
            
            embed.set_footer(text="新着メール通知")

            print(f"[DEBUG] 通知を送信: {subject}")
            # 通知を送信
            await channel.send(
                f"<@{connection.user_id}>さん宛のメールが届きました",
                embed=embed
            )

        except Exception as e:
            print(f"[ERROR] Discord通知でエラー発生: {e}")

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MailSchedulerCog(bot)) 