import os
from typing import Optional

import discord
from discord import app_commands
from dotenv import load_dotenv

from .commands.task import task_add
from .tasks.notification import NotificationManager


class TodoBot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)
        self.notification_manager: Optional[NotificationManager] = None

    async def setup_hook(self):
        """Botの初期設定"""
        # コマンドを登録
        self.tree.add_command(task_add)
        
        # 通知マネージャーを初期化
        self.notification_manager = NotificationManager(self)

        # コマンドをグローバルに同期
        await self.tree.sync()


def run_bot():
    """Botを起動する"""
    load_dotenv()

    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise ValueError("DISCORD_TOKEN is not set in environment variables")

    bot = TodoBot()
    bot.run(token) 