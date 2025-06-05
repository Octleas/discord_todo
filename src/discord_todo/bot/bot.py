from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from ..config import settings
from ..tasks.notification import NotificationManager


class TodoBot(commands.Bot):
    """タスク管理Bot"""

    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None,
        )
        self.notification_manager: Optional[NotificationManager] = None

    async def setup_hook(self) -> None:
        """Botの初期設定"""
        print("setup_hook呼び出し")  # デバッグ用
        # コグの読み込み
        await self.load_extension("discord_todo.bot.cogs.task")
        await self.load_extension("discord_todo.bot.cogs.mail")

        # 通知マネージャーを初期化（1分ごとの通知チェックを開始）
        self.notification_manager = NotificationManager(self)

        # コマンドの同期（グローバル登録）
        await self.tree.sync()

    async def on_ready(self) -> None:
        """Bot起動時の処理"""
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        print("------")


async def run_bot() -> None:
    """Botを起動"""
    async with TodoBot() as bot:
        await bot.start(settings.DISCORD_TOKEN) 