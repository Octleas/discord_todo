from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands
from ..config import settings
import logging
import asyncio

from ..tasks.notification import NotificationManager

# ロガーの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DiscordBot(commands.Bot):
    """タスク管理Bot"""

    def __init__(self) -> None:
        logger.info("Botの初期化を開始")
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None,
        )
        self.notification_manager: Optional[NotificationManager] = None
        logger.info("Botの初期化完了")

    async def setup_hook(self) -> None:
        """Botの初期設定"""
        logger.info("setup_hook開始")
        
        # Cogの登録
        await self.load_extension("discord_todo.bot.cogs.task")
        logger.info("task cogを読み込みました")
        
        await self.load_extension("discord_todo.bot.cogs.mail")
        logger.info("mail cogを読み込みました")
        
        await self.load_extension("discord_todo.bot.cogs.mail_scheduler")
        logger.info("mail_scheduler cogを読み込みました")

        # スラッシュコマンドの同期（開発環境のみ）
        if settings.ENVIRONMENT == "development":
            logger.info("スラッシュコマンドの同期を開始します...")
            try:
                if settings.DISCORD_DEVELOPMENT_GUILD_ID:
                    guild = discord.Object(id=settings.DISCORD_DEVELOPMENT_GUILD_ID)
                    # 特定のギルドのみに同期（高速）
                    self.tree.copy_global_to(guild=guild)
                    await self.tree.sync(guild=guild)
                    logger.info(f"ギルド {settings.DISCORD_DEVELOPMENT_GUILD_ID} にコマンドを同期しました")
                else:
                    # グローバルコマンドの同期（時間がかかる）
                    logger.warning("開発ギルドIDが設定されていないため、グローバルコマンドの同期を行います（時間がかかります）")
                    await self.tree.sync()
                    logger.info("グローバルコマンドの同期が完了しました")
            except discord.HTTPException as e:
                logger.error(f"コマンドの同期中にエラーが発生: {e}")
            except Exception as e:
                logger.error(f"予期せぬエラーが発生: {e}")
        
        logger.info("setup_hook完了")

    async def on_ready(self) -> None:
        """Bot起動時の処理"""
        logger.info(f"{self.user} としてログインしました (ID: {self.user.id})")
        logger.info("------")

async def start_bot():
    """Botを起動（非同期版）"""
    bot = DiscordBot()
    try:
        async with bot:
            await bot.start(settings.DISCORD_TOKEN)
    except Exception as e:
        logger.error(f"Bot起動中にエラーが発生: {e}")
        raise

def run_bot():
    """Botを起動（同期版）"""
    try:
        asyncio.run(start_bot())
    except KeyboardInterrupt:
        logger.info("Botを終了します")
    except Exception as e:
        logger.error(f"予期せぬエラーが発生: {e}")
        raise 