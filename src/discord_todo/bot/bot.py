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
        self._commands_cleared = False  # コマンドクリア済みフラグ
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

        logger.info("setup_hook完了")

    async def on_ready(self) -> None:
        """Bot起動時の処理"""
        logger.info(f"{self.user} としてログインしました (ID: {self.user.id})")
        
        # 初回起動時のみコマンドクリアと同期を実行
        if not self._commands_cleared:
            await self._clear_and_sync_commands()
            self._commands_cleared = True
        
        logger.info("------")
        
    async def _clear_and_sync_commands(self) -> None:
        """コマンドのクリアと同期処理"""
        logger.info("重複コマンドをクリアして再同期します...")
        
        # 現在ロードされているコマンドを確認
        logger.info(f"現在ロードされているコマンド数: {len(self.tree.get_commands())}")
        for cmd in self.tree.get_commands():
            logger.info(f"  - /{cmd.name}: {cmd.description}")
        
        try:
            if settings.DISCORD_DEVELOPMENT_GUILD_ID:
                guild = discord.Object(id=settings.DISCORD_DEVELOPMENT_GUILD_ID)
                
                # 1. ギルドコマンドのみをクリア（グローバルはそのまま）
                logger.info("ギルドコマンドをクリア中...")
                self.tree.clear_commands(guild=guild)
                await self.tree.sync(guild=guild)
                logger.info(f"ギルド {settings.DISCORD_DEVELOPMENT_GUILD_ID} のコマンドをクリアしました")
                
                # 2. 少し待機
                logger.info("3秒待機中...")
                await asyncio.sleep(3)
                
                # 3. コマンドを直接ギルドに同期（リトライ機能付き）
                logger.info("コマンドを再同期中...")
                logger.info(f"同期前のコマンド数確認: {len(self.tree.get_commands())}")
                
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        # グローバルコマンドをギルドにコピー
                        self.tree.copy_global_to(guild=guild)
                        logger.info("グローバルコマンドをギルドにコピーしました")
                        
                        synced = await asyncio.wait_for(
                            self.tree.sync(guild=guild),
                            timeout=30.0  # 30秒でタイムアウト
                        )
                        logger.info(f"ギルド {settings.DISCORD_DEVELOPMENT_GUILD_ID} に {len(synced)} 個のコマンドを同期しました")
                        
                        # 同期されたコマンド一覧をログ出力
                        for cmd in synced:
                            logger.info(f"  ✅ /{cmd.name}: {cmd.description}")
                        break
                        
                    except asyncio.TimeoutError:
                        logger.warning(f"同期がタイムアウトしました（試行 {attempt + 1}/{max_retries}）")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(2)
                        else:
                            logger.error("同期が最大試行回数でも失敗しました")
                            
                    except Exception as e:
                        logger.error(f"同期中にエラー（試行 {attempt + 1}/{max_retries}）: {e}")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(2)
                        else:
                            raise
            else:
                # グローバル同期のみ
                self.tree.clear_commands(guild=None)
                await self.tree.sync()
                logger.info("グローバルコマンドをクリアしました")
                
                await asyncio.sleep(5)
                
                synced = await self.tree.sync()
                logger.info(f"{len(synced)} 個のグローバルコマンドを同期しました")
                
        except discord.HTTPException as e:
            logger.error(f"コマンド同期中にHTTPエラーが発生: {e}")
        except Exception as e:
            logger.error(f"コマンド同期中に予期せぬエラーが発生: {e}")

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