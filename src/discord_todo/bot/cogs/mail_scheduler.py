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

    @app_commands.command(name="mail-test", description="メール取得のテストを実行します")
    @app_commands.describe(
        limit="取得するメールの数（1-50）",
        skip_notification="通知を送信せずに取得のみ行う場合はTrue"
    )
    async def test_mail_fetch(
        self,
        interaction: discord.Interaction,
        limit: app_commands.Range[int, 1, 50] = 10,
        skip_notification: bool = False
    ) -> None:
        """メール取得のテストを実行するコマンド"""
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

                # メール取得テスト
                try:
                    mails = await self.fetch_user_mails(
                        connection,
                        session,
                        limit=limit,
                        skip_notification=skip_notification
                    )
                    
                    # 取得結果のサマリーを送信
                    summary = f"メール取得テストが完了しました。\n"
                    summary += f"- 取得したメール数: {len(mails)}\n"
                    if not skip_notification:
                        summary += "- 通知チャンネルを確認してください。"
                    else:
                        # 通知をスキップした場合は、件名一覧を表示
                        summary += "\n取得したメール：\n"
                        for mail in mails[:5]:  # 最初の5件のみ表示
                            subject = mail["subject"]
                            sender = mail["from"]["emailAddress"]["address"]
                            summary += f"- {subject} (From: {sender})\n"
                        if len(mails) > 5:
                            summary += f"...他 {len(mails) - 5} 件"
                    
                    await interaction.followup.send(summary, ephemeral=True)
                except Exception as e:
                    await interaction.followup.send(
                        f"メール取得テストでエラーが発生しました：{str(e)}",
                        ephemeral=True
                    )
        except Exception as e:
            await interaction.followup.send(
                f"エラーが発生しました：{str(e)}",
                ephemeral=True
            )

    async def fetch_all_mails(self):
        """全ユーザーのメールを取得"""
        try:
            async with AsyncSessionLocal() as session:
                # 有効な連携を全て取得
                current_time = to_utc(datetime.now())
                result = await session.execute(
                    select(MailConnection).where(
                        MailConnection.token_expires_at > current_time
                    )
                )
                connections = result.scalars().all()

                for connection in connections:
                    try:
                        await self.fetch_user_mails(connection, session)
                    except Exception as e:
                        print(f"[ERROR] ユーザー {connection.user_id} のメール取得に失敗: {e}")
                        continue

        except Exception as e:
            print(f"[ERROR] メール一括取得処理でエラー発生: {e}")

    async def fetch_user_mails(
        self,
        connection: MailConnection,
        session,
        limit: int = 10,
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
                "$top": min(50, limit),  # 最大50件まで
                "$orderby": "receivedDateTime desc",
                "$select": "subject,from,receivedDateTime,id"
            }

            print(f"[DEBUG] メール取得APIを呼び出し: {url}")
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, params=params)
                print(f"[DEBUG] API応答ステータス: {response.status_code}")
                
                if response.status_code != 200:
                    print(f"[ERROR] メール取得APIでエラー: {response.text}")
                    return []

                mails = response.json().get("value", [])
                print(f"[DEBUG] 取得したメール数: {len(mails)}")
                
                if not skip_notification:
                    # 取得したメールをDiscordに通知
                    guild = self.bot.get_guild(int(connection.guild_id))
                    if not guild:
                        print(f"[ERROR] Guild not found: {connection.guild_id}")
                        return mails

                    for mail in mails:
                        await self.notify_mail(guild, connection, mail)

            # 最終チェック時刻を更新
            connection.last_checked_at = to_utc(datetime.now())
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
            embed = discord.Embed(
                title=mail["subject"],
                color=discord.Color.blue(),
                timestamp=datetime.fromisoformat(mail["receivedDateTime"].replace("Z", "+00:00"))
            )
            
            sender = mail["from"]["emailAddress"]
            embed.add_field(
                name="送信者",
                value=f"{sender.get('name', 'Unknown')} ({sender.get('address', 'No address')})",
                inline=False
            )

            print(f"[DEBUG] 通知を送信: {mail['subject']}")
            # 通知を送信
            await channel.send(
                f"<@{connection.user_id}>さん宛のメールが届きました：",
                embed=embed
            )

        except Exception as e:
            print(f"[ERROR] Discord通知でエラー発生: {e}")

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MailSchedulerCog(bot)) 