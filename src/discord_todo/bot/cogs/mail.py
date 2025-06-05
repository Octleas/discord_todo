from datetime import datetime, timedelta
import urllib.parse

import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy import select

from ...db.session import AsyncSessionLocal
from ...models.mail import MailConnection
from ...config import settings


class MailCog(commands.Cog):
    """メール連携コグ"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="mail-connect", description="Outlook連携の認証URLを発行します")
    async def mail_connect(self, interaction: discord.Interaction) -> None:
        """Outlook認証用のURLを案内するコマンド"""
        client_id = settings.MICROSOFT_CLIENT_ID
        tenant_id = settings.MICROSOFT_TENANT_ID
        redirect_uri = "http://localhost:8000/api/mail/callback"
        scope = "offline_access Mail.Read User.Read"
        response_type = "code"
        prompt = "consent"
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

        await interaction.response.send_message(
            f"Outlook連携のため、以下のURLから認証を行ってください:\n{url}",
            ephemeral=True
        )

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
        if connection.token_expires_at - datetime.utcnow() < timedelta(days=7):
            embed.add_field(
                name="⚠️ 警告",
                value="トークンの有効期限が近づいています。`/mail-refresh`コマンドで更新してください。",
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
                    "メール連携が設定されていません。", ephemeral=True
                )
                return

            await session.delete(connection)
            await session.commit()

        await interaction.response.send_message(
            "メール連携を解除しました。", ephemeral=True
        )


async def setup(bot: commands.Bot) -> None:
    """コグのセットアップ"""
    await bot.add_cog(MailCog(bot)) 