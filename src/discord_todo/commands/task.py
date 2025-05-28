import re
from datetime import datetime, timedelta
from typing import List, Optional

import discord
from discord import app_commands
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import ImportanceLevel, Task, TaskStatus
from ..utils.date_parser import parse_datetime
from ..utils.notification import parse_notification_time


@app_commands.command(name="task-add", description="タスクを追加します")
@app_commands.describe(
    title="タスクのタイトル",
    assigned_to="担当者（メンションで指定）",
    deadline="締切日時（例: 2024-03-20 15:00）",
    notifications="通知タイミング（例: 1h 30m 1d）スペース区切りで複数指定可能",
    importance="タスクの重要度",
    summary="タスクの詳細な説明（省略可）",
)
async def task_add(
    interaction: discord.Interaction,
    title: str,
    assigned_to: str,
    deadline: str,
    notifications: Optional[str] = None,
    importance: ImportanceLevel = ImportanceLevel.MEDIUM,
    summary: Optional[str] = None,
) -> None:
    """タスクを追加するコマンド"""
    try:
        deadline_dt = parse_datetime(deadline)
    except ValueError as e:
        await interaction.response.send_message(f"日時の形式が正しくありません: {e}", ephemeral=True)
        return

    # 通知時間の解析
    notification_minutes: List[int] = []
    if notifications:
        try:
            notification_minutes = [
                parse_notification_time(time_str)
                for time_str in notifications.split()
            ]
            notification_minutes.sort(reverse=True)  # 大きい順（早い通知順）にソート
        except ValueError as e:
            await interaction.response.send_message(
                f"通知時間の形式が正しくありません: {e}", ephemeral=True
            )
            return

    # メンションからユーザーIDを抽出
    user_id_match = re.match(r"<@!?(\d+)>", assigned_to)
    if not user_id_match:
        await interaction.response.send_message(
            "担当者はメンションで指定してください（例: @username）", ephemeral=True
        )
        return

    user_id = user_id_match.group(1)

    async with AsyncSession() as session:
        task = Task(
            guild_id=str(interaction.guild_id),
            channel_id=str(interaction.channel_id),
            message_id="temporary",  # 後で更新
            title=title,
            assigned_to=user_id,
            deadline=deadline_dt,
            importance=importance,
            summary=summary,
            notification_times=notification_minutes,
        )
        session.add(task)
        await session.flush()  # IDを生成するためにflush

        # 通知時間の文字列を生成
        notification_str = ""
        if notification_minutes:
            times = []
            for minutes in notification_minutes:
                if minutes >= 1440:  # 1日以上
                    times.append(f"{minutes // 1440}日前")
                elif minutes >= 60:  # 1時間以上
                    times.append(f"{minutes // 60}時間前")
                else:
                    times.append(f"{minutes}分前")
            notification_str = f"\n通知: {', '.join(times)}"

        embed = discord.Embed(
            title="タスクが追加されました",
            color=discord.Color.green(),
            timestamp=datetime.now(),
        )
        embed.add_field(name="ID", value=task.short_id, inline=True)
        embed.add_field(name="タイトル", value=title, inline=True)
        embed.add_field(name="担当者", value=assigned_to, inline=True)
        embed.add_field(
            name="締切", value=deadline_dt.strftime("%Y-%m-%d %H:%M"), inline=True
        )
        embed.add_field(name="重要度", value=importance.value, inline=True)
        if summary:
            embed.add_field(name="詳細", value=summary, inline=False)
        if notification_str:
            embed.add_field(name="通知設定", value=notification_str, inline=False)

        # メッセージを送信
        await interaction.response.send_message(embed=embed)
        message = await interaction.original_response()
        
        # メッセージIDを更新
        task.message_id = str(message.id)
        await session.commit() 