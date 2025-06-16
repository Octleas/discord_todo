from datetime import datetime, timedelta, timezone
import urllib.parse

import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy import select
import httpx

from ...db.session import AsyncSessionLocal
from ...models.mail import MailConnection
from ...config import settings


def to_utc(dt: datetime) -> datetime:
    """日時をUTCのタイムゾーン付きに変換"""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


async def ensure_valid_access_token(connection: MailConnection, session) -> str:
    """アクセストークンの有効性を確認し、必要に応じて更新する"""
    # タイムゾーンを統一してチェック
    expires_at = to_utc(connection.token_expires_at)
    now = datetime.now(timezone.utc)
    
    if expires_at - now < timedelta(minutes=5):
        print(f"[DEBUG] トークン期限切れ間近。リフレッシュ実行: {expires_at} < {now}")
        
        # 共通エンドポイントを使用
        token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
        # スコープを完全なURL形式に修正
        scope = "https://graph.microsoft.com/Mail.Read https://graph.microsoft.com/User.Read offline_access openid profile"
        data = {
            "client_id": settings.MICROSOFT_CLIENT_ID,
            "client_secret": settings.MICROSOFT_CLIENT_SECRET,
            "grant_type": "refresh_token",
            "refresh_token": connection.refresh_token,
            "redirect_uri": "http://localhost:8000/api/mail/callback",
            "scope": scope,
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(token_url, data=data)
                
                if response.status_code != 200:
                    print(f"[ERROR] トークンリフレッシュ失敗: {response.text}")
                    raise Exception(f"トークンリフレッシュ失敗: {response.text}")
                
                token_data = response.json()
                print(f"[DEBUG] トークンリフレッシュ成功")
                
                connection.access_token = token_data["access_token"]
                connection.refresh_token = token_data["refresh_token"]
                # タイムゾーン統一（UTC naiveで保存）
                new_expires = datetime.now(timezone.utc) + timedelta(seconds=token_data["expires_in"])
                connection.token_expires_at = new_expires.replace(tzinfo=None)
                await session.commit()
                
            except Exception as e:
                print(f"[ERROR] トークン更新例外: {e}")
                raise
    else:
        print(f"[DEBUG] トークンはまだ有効: {expires_at}")
    
    return connection.access_token


class MailCog(commands.Cog):
    """メール連携コグ"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="mail-connect", description="Microsoftメールの連携設定")
    async def mail_connect(self, interaction: discord.Interaction) -> None:
        """Microsoftメール認証用のURLを案内するコマンド"""
        try:
            client_id = settings.MICROSOFT_CLIENT_ID
            # 共通エンドポイントを使用
            tenant_id = "common"
            redirect_uri = "http://localhost:8000/api/mail/callback"
            # スコープを完全なURL形式に修正
            scope = "https://graph.microsoft.com/Mail.Read https://graph.microsoft.com/User.Read offline_access openid profile"
            response_type = "code"
            prompt = "select_account"  # アカウント選択画面を強制表示
            guild_id = str(interaction.guild_id)
            user_id = str(interaction.user.id)
            state = f"{guild_id}:{user_id}"
            params = {
                "client_id": client_id,
                "response_type": response_type,
                "redirect_uri": redirect_uri,
                "response_mode": "query",
                "scope": scope,
                "prompt": prompt,
                "state": state,
            }
            url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize?{urllib.parse.urlencode(params)}"

            embed = discord.Embed(
                title="Microsoftメール連携",
                description="以下のURLから認証を行ってください。\n\n"
                           "**重要な注意事項：**\n"
                           "• 個人用Microsoftアカウント（outlook.com等）でログインしてください\n"
                           "• ブラウザのキャッシュをクリアしてから試してください\n"
                           "• シークレットモードでの認証を推奨します",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="認証URL",
                value=url,
                inline=False
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            print(f"[ERROR] 認証URL生成エラー: {e}")
            error_embed = discord.Embed(
                title="エラーが発生しました",
                description=f"認証URLの生成中にエラーが発生しました。\n```{str(e)}```",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)

    @app_commands.command(name="mail-status", description="メール連携の状態を確認")
    async def mail_status(self, interaction: discord.Interaction) -> None:
        """メール連携の状態を確認するコマンド"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(MailConnection).where(
                    MailConnection.guild_id == str(interaction.guild_id),
                    MailConnection.user_id == str(interaction.user.id),
                )
            )
            connection = result.scalar_one_or_none()

        if not connection:
            await interaction.response.send_message(
                "メール連携が設定されていません。`/mail-connect`コマンドで設定してください。",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title="メール連携状態",
            color=discord.Color.blue(),
        )
        embed.add_field(name="連携メールアドレス", value=connection.email, inline=True)
        embed.add_field(
            name="最終チェック日時",
            value=to_utc(connection.last_checked_at).strftime("%Y-%m-%d %H:%M UTC")
            if connection.last_checked_at
            else "未チェック",
            inline=True,
        )
        embed.add_field(
            name="トークン有効期限",
            value=to_utc(connection.token_expires_at).strftime("%Y-%m-%d %H:%M UTC"),
            inline=True,
        )

        # トークンの有効期限が近い場合は警告
        expires_at = to_utc(connection.token_expires_at)
        now = datetime.now(timezone.utc)
        if expires_at - now < timedelta(days=7):
            embed.add_field(
                name="⚠️ 警告",
                value="トークンの有効期限が近づいています。`/mail-connect`で再認証してください。",
                inline=False,
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="mail-test", description="メール取得のテストを実行")
    @app_commands.describe(
        limit="取得するメールの数（1-10）",
        show_content="メールの内容を表示するかどうか"
    )
    async def mail_test(
        self,
        interaction: discord.Interaction,
        limit: app_commands.Range[int, 1, 10] = 5,
        show_content: bool = False
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

                print(f"[DEBUG] メール取得テスト開始 - ユーザー: {connection.email}")

                # アクセストークンの有効性確認
                access_token = await ensure_valid_access_token(connection, session)
                
                # Microsoft Graph APIでメール取得
                url = "https://graph.microsoft.com/v1.0/me/messages"
                headers = {"Authorization": f"Bearer {access_token}"}
                params = {
                    "$top": limit,
                    "$orderby": "receivedDateTime desc",
                    "$select": "subject,from,receivedDateTime,bodyPreview" if show_content else "subject,from,receivedDateTime"
                }

                async with httpx.AsyncClient() as client:
                    response = await client.get(url, headers=headers, params=params)
                    
                    if response.status_code != 200:
                        error_msg = f"メール取得APIエラー: {response.status_code} - {response.text}"
                        print(f"[ERROR] {error_msg}")
                        await interaction.followup.send(
                            f"メール取得に失敗しました:\n```{error_msg}```",
                            ephemeral=True
                        )
                        return

                    mail_data = response.json()
                    mails = mail_data.get("value", [])
                    
                    print(f"[DEBUG] 取得したメール数: {len(mails)}")

                # 結果を表示
                if not mails:
                    await interaction.followup.send(
                        "メールが見つかりませんでした。",
                        ephemeral=True
                    )
                    return

                # Embedで結果を表示
                embed = discord.Embed(
                    title=f"📧 メール取得テスト結果",
                    description=f"連携アカウント: {connection.email}\n取得件数: {len(mails)}件",
                    color=discord.Color.green()
                )

                for i, mail in enumerate(mails, 1):
                    subject = mail.get("subject", "件名なし")[:100]
                    sender_info = mail.get("from", {}).get("emailAddress", {})
                    sender = sender_info.get("address", "不明な送信者")
                    received = mail.get("receivedDateTime", "")
                    
                    # 日時のフォーマット
                    try:
                        received_dt = datetime.fromisoformat(received.replace("Z", "+00:00"))
                        received_str = received_dt.strftime("%m/%d %H:%M")
                    except:
                        received_str = "日時不明"

                    field_value = f"**送信者:** {sender}\n**受信時刻:** {received_str}"
                    
                    if show_content:
                        preview = mail.get("bodyPreview", "")[:100]
                        if preview:
                            field_value += f"\n**プレビュー:** {preview}..."

                    embed.add_field(
                        name=f"{i}. {subject}",
                        value=field_value,
                        inline=False
                    )

                # 最終チェック時刻を更新
                connection.last_checked_at = datetime.now(timezone.utc).replace(tzinfo=None)
                await session.commit()

                await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            print(f"[ERROR] メール取得テストでエラー: {e}")
            await interaction.followup.send(
                f"エラーが発生しました:\n```{str(e)}```",
                ephemeral=True
            )

    @app_commands.command(name="mail-disconnect", description="メール連携を解除")
    async def mail_disconnect(self, interaction: discord.Interaction) -> None:
        """メール連携を解除するコマンド"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(MailConnection).where(
                    MailConnection.guild_id == str(interaction.guild_id),
                    MailConnection.user_id == str(interaction.user.id),
                )
            )
            connection = result.scalar_one_or_none()

            if not connection:
                await interaction.response.send_message(
                    "メール連携が設定されていません。",
                    ephemeral=True
                )
                return

            await session.delete(connection)
            await session.commit()

        await interaction.response.send_message(
            "メール連携を解除しました。",
            ephemeral=True
        )


async def setup(bot: commands.Bot) -> None:
    """コグのセットアップ"""
    await bot.add_cog(MailCog(bot)) 