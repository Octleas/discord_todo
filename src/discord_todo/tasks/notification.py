from datetime import datetime, timedelta
from typing import List

import discord
from discord.ext import tasks
from sqlalchemy import select
from ..db.session import AsyncSessionLocal

from ..models import Task, TaskStatus


class NotificationManager:
    """タスク通知を管理するクラス"""

    def __init__(self, bot: discord.Client):
        print("NotificationManager初期化")  # デバッグ用
        self.bot = bot
        self.check_notifications.start()

    def cog_unload(self):
        self.check_notifications.cancel()

    @tasks.loop(hours=1)  # 1時間ごとにチェック
    async def check_notifications(self):
        try:
            print("通知チェック開始")  # デバッグ用
            now = datetime.now()
            # 現在時刻を時間単位に丸める（分以下を0にする）
            now = now.replace(minute=0, second=0, microsecond=0)

            async with AsyncSessionLocal() as session:
                # 未完了のタスクを取得
                query = select(Task).where(
                    Task.status == TaskStatus.PENDING,
                )
                result = await session.execute(query)
                tasks: List[Task] = result.scalars().all()

                for task in tasks:
                    print(f"タスク: {task.title}, 通知タイミング: {task.notification_times}, 通知済: {task.notified_times}")  # デバッグ用
                    for minutes in task.notification_times:
                        notify_at = task.deadline - timedelta(minutes=minutes)
                        # 通知時刻を時間単位に丸める
                        notify_at = notify_at.replace(minute=0, second=0, microsecond=0)
                        print(f"通知予定時刻: {notify_at}, 現在時刻: {now}")  # デバッグ用

                        # 通知時刻が現在時刻と一致し、まだ通知していない場合
                        if notify_at == now and minutes not in task.notified_times:
                            print("通知送信処理に入る")  # デバッグ用
                            # 通知を送信
                            channel = self.bot.get_channel(int(task.channel_id))
                            if channel:
                                time_str = (
                                    f"{minutes // 1440}日"
                                    if minutes >= 1440
                                    else f"{minutes // 60}時間"
                                )
                                
                                embed = discord.Embed(
                                    title="タスク通知",
                                    description=f"タスク「{task.title}」の期限まであと{time_str}です",
                                    color=discord.Color.yellow(),
                                )
                                embed.add_field(name="ID", value=task.short_id, inline=True)
                                embed.add_field(
                                    name="担当者", value=f"<@{task.assigned_to}>", inline=True
                                )
                                embed.add_field(
                                    name="締切",
                                    value=task.deadline.strftime("%Y-%m-%d %H:%M"),
                                    inline=True,
                                )
                                
                                await channel.send(
                                    content=f"<@{task.assigned_to}>",
                                    embed=embed,
                                )
                                print("通知送信完了")  # デバッグ用
                                # 通知済みとしてマーク
                                task.notified_times.append(minutes)
                                await session.commit()
        except Exception as e:
            print(f"通知チェックで例外発生: {e}")

    @check_notifications.before_loop
    async def before_check_notifications(self):
        """Botの準備が完了するまで待機"""
        await self.bot.wait_until_ready() 