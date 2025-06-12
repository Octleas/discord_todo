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


async def ensure_valid_access_token(connection: MailConnection, session) -> str:
    """アクセストークンの有効性を確認し、必要に応じて更新する"""
    # 期限が5分未満ならリフレッシュ
    if connection.token_expires_at - datetime.now(timezone.utc) < timedelta(minutes=5):
        token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
        data = {
            "client_id": settings.MICROSOFT_CLIENT_ID,
            "client_secret": settings.MICROSOFT_CLIENT_SECRET,
            "grant_type": "refresh_token",
            "refresh_token": connection.refresh_token,
            "redirect_uri": "http://localhost:8000/api/mail/callback",
            "scope": "openid profile offline_access Mail.Read User.Read",
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data=data)
            if response.status_code != 200:
                raise Exception(f"トークンリフレッシュ失敗: {response.text}")
            
            token_data = response.json()
            access_token = token_data.get("access_token")
            refresh_token = token_data.get("refresh_token")
            expires_in = token_data.get("expires_in")
            
            if not access_token or not refresh_token or not expires_in:
                raise Exception("トークン情報の取得に失敗しました")
            
            # トークン情報を更新
            connection.access_token = access_token
            connection.refresh_token = refresh_token
            connection.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
            await session.commit()
    
    return connection.access_token


class MailCog(commands.Cog):
    """メール連携コグ"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="mail-connect", description="Outlook連携の認証URLを発行します")
    async def mail_connect(self, interaction: discord.Interaction) -> None:
        """Outlook認証用のURLを案内するコマンド"""
        client_id = settings.MICROSOFT_CLIENT_ID
        tenant_id = "common"
        redirect_uri = "http://localhost:8000/api/mail/callback"
        scope = "openid profile offline_access Mail.Read User.Read"
        response_type = "code"
        prompt = "consent"  # 明示的な同意を要求
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
            "domain_hint": "ed.ritsumei.ac.jp",
            "login_hint": f"rp0139rh@ed.ritsumei.ac.jp",  # ログインヒントを追加
        }
        url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize?{urllib.parse.urlencode(params)}"

        embed = discord.Embed(
            title="Outlook連携の認証",
            description="以下のURLから認証を行ってください。\n\n**このアプリケーションについて：**\n"
                       "• このアプリは、メール通知のみを目的としています\n"
                       "• メールの読み取り権限のみを要求します\n"
                       "• メールの内容は安全に保管され、通知以外の目的では使用されません",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="要求する権限",
            value="• メールの読み取り（Mail.Read）\n"
                 "• プロフィールの読み取り（User.Read）\n"
                 "• オフラインアクセス（自動更新用）",
            inline=False
        )
        embed.add_field(
            name="認証URL",
            value=url,
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

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
            value=connection.last_checked_at.strftime("%Y-%m-%d %H:%M")
            if connection.last_checked_at
            else "未チェック",
            inline=True,
        )
        embed.add_field(
            name="トークン有効期限",
            value=connection.token_expires_at.strftime("%Y-%m-%d %H:%M"),
            inline=True,
        )

        # トークンの有効期限が近い場合は警告
        if connection.token_expires_at - datetime.now(timezone.utc) < timedelta(days=7):
            embed.add_field(
                name="⚠️ 警告",
                value="トークンの有効期限が近づいています。`/mail-connect`で再認証してください。",
                inline=False,
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

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