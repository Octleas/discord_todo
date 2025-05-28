import asyncio

from .bot.bot import run_bot


def main() -> None:
    """メインエントリーポイント"""
    asyncio.run(run_bot())


if __name__ == "__main__":
    main() 