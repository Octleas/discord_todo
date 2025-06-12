from datetime import datetime
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy import select

from ...db.session import AsyncSessionLocal
from ...models.task import ImportanceLevel, Task, TaskStatus
from ...config import settings


class TaskCog(commands.Cog):
    """タスク管理コグ"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="task-add", description="新しいタスクを追加")
    @app_commands.describe(
        title="タスクのタイトル",
        assigned_to="担当者（メンション）",
        deadline="締め切り（YYYY-MM-DD HH:MM形式）",
        notifications="通知タイミング（例: 1h 2h）",
        importance="重要度",
        summary="タスクの詳細説明",
    )
    async def add_task(
        self,
        interaction: discord.Interaction,
        title: str,
        assigned_to: discord.Member,
        deadline: str,
        notifications: Optional[str] = None,
        importance: ImportanceLevel = ImportanceLevel.MEDIUM,
        summary: Optional[str] = None,
    ) -> None:
        """新しいタスクを追加するコマンド"""
        try:
            deadline_dt = datetime.strptime(deadline, "%Y-%m-%d %H:%M")
        except ValueError:
            await interaction.response.send_message(
                "締め切りの形式が正しくありません。YYYY-MM-DD HH:MM形式で入力してください。",
                ephemeral=True,
            )
            return

        # 通知時間のパース
        notification_minutes = []
        notification_str = ""
        if notifications:
            try:
                from ...utils.notification import parse_notification_time
                notification_minutes = [
                    parse_notification_time(time_str)
                    for time_str in notifications.split()
                ]
                notification_minutes.sort(reverse=True)
                # 表示用文字列生成
                times = []
                for minutes in notification_minutes:
                    if minutes >= 1440:
                        times.append(f"{minutes // 1440}日前")
                    elif minutes >= 60:
                        times.append(f"{minutes // 60}時間前")
                    else:
                        times.append(f"{minutes}分前")
                notification_str = f"\n通知: {', '.join(times)}"
            except Exception as e:
                await interaction.response.send_message(
                    f"通知時間の形式が正しくありません: {e}", ephemeral=True
                )
                return

        async with AsyncSessionLocal() as session:
            task = Task(
                guild_id=str(interaction.guild_id),
                channel_id=str(interaction.channel_id),
                message_id=str(interaction.id),
                title=title,
                assigned_to=str(assigned_to.id),
                deadline=deadline_dt,
                importance=importance,
                summary=summary,
                notification_times=notification_minutes,
            )
            session.add(task)
            await session.commit()

        embed = discord.Embed(
            title="新しいタスク",
            description=title,
            color=discord.Color.green(),
        )
        embed.add_field(name="担当者", value=assigned_to.mention, inline=True)
        embed.add_field(name="締め切り", value=deadline, inline=True)
        embed.add_field(name="重要度", value=importance.value, inline=True)
        if summary:
            embed.add_field(name="詳細", value=summary, inline=False)
        if notification_str:
            embed.add_field(name="通知設定", value=notification_str, inline=False)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="task-list", description="タスク一覧を表示")
    @app_commands.describe(
        status="表示するタスクのステータス",
        assigned_to="担当者でフィルター（メンション）",
    )
    async def list_tasks(
        self,
        interaction: discord.Interaction,
        status: Optional[TaskStatus] = None,
        assigned_to: Optional[discord.Member] = None,
    ) -> None:
        """タスク一覧を表示するコマンド"""
        async with AsyncSessionLocal() as session:
            query = select(Task).where(Task.guild_id == str(interaction.guild_id))

            if status:
                query = query.where(Task.status == status)
            if assigned_to:
                query = query.where(Task.assigned_to == str(assigned_to.id))

            result = await session.execute(query)
            tasks = result.scalars().all()

        if not tasks:
            await interaction.response.send_message(
                "タスクが見つかりませんでした。", ephemeral=True
            )
            return

        embeds = []
        for task in tasks:
            embed = discord.Embed(
                title=f"({task.short_id}) {task.title}",
                description=task.summary if task.summary else "詳細なし",
                color=discord.Color.blue(),
            )
            assigned_member = interaction.guild.get_member(int(task.assigned_to))
            
            # 担当者・重要度を横並び
            embed.add_field(
                name="担当者",
                value=assigned_member.mention if assigned_member else '不明',
                inline=True,
            )
            embed.add_field(
                name="重要度",
                value=task.importance.value,
                inline=True,
            )
            # 空白フィールドで改行を強制（2列で折り返し）
            embed.add_field(name="\u200b", value="\u200b", inline=False)

            # 作成日・締切日を横並び
            embed.add_field(
                name="作成日",
                value=task.created_at.strftime('%Y-%m-%d %H:%M'),
                inline=True,
            )
            embed.add_field(
                name="締切日",
                value=task.deadline.strftime('%Y-%m-%d %H:%M'),
                inline=True,
            )
            embed.add_field(name="\u200b", value="\u200b", inline=False)

            # ステータスは1行で
            embed.add_field(
                name="ステータス",
                value=task.status.value,
                inline=False,
            )
            embeds.append(embed)

        await interaction.response.send_message(embeds=embeds[:10])

    @app_commands.command(name="task-complete", description="タスクを完了にする")
    @app_commands.describe(task_id="完了にするタスクのID")
    async def complete_task(
        self,
        interaction: discord.Interaction,
        task_id: int,
    ) -> None:
        """タスクを完了にするコマンド"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Task).where(
                    Task.id == task_id,
                    Task.guild_id == str(interaction.guild_id),
                )
            )
            task = result.scalar_one_or_none()

            if not task:
                await interaction.response.send_message(
                    "指定されたタスクが見つかりませんでした。", ephemeral=True
                )
                return

            if task.assigned_to != str(interaction.user.id):
                await interaction.response.send_message(
                    "このタスクの担当者ではありません。", ephemeral=True
                )
                return

            task.status = TaskStatus.COMPLETED
            await session.commit()

        embed = discord.Embed(
            title="タスク完了",
            description=task.title,
            color=discord.Color.green(),
        )
        embed.add_field(name="完了者", value=interaction.user.mention, inline=True)
        embed.add_field(
            name="完了日時", value=datetime.utcnow().strftime("%Y-%m-%d %H:%M"), inline=True
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="task-delete", description="タスクを削除します")
    @app_commands.describe(task_id="削除するタスクのID")
    async def delete_task(
        self,
        interaction: discord.Interaction,
        task_id: int,
    ) -> None:
        """タスクを削除するコマンド"""
        async with AsyncSessionLocal() as session:
            # タスクの存在確認
            result = await session.execute(
                select(Task).where(
                    Task.id == task_id,
                    Task.guild_id == str(interaction.guild_id),
                )
            )
            task = result.scalar_one_or_none()

            if not task:
                await interaction.response.send_message(
                    "指定されたタスクが見つかりませんでした。", ephemeral=True
                )
                return

            # 権限チェック（タスクの担当者またはサーバー管理者のみ削除可能）
            if not (
                str(interaction.user.id) == task.assigned_to
                or interaction.user.guild_permissions.administrator
            ):
                await interaction.response.send_message(
                    "このタスクを削除する権限がありません。タスクの担当者またはサーバー管理者のみが削除できます。",
                    ephemeral=True,
                )
                return

            # タスクの削除
            await session.delete(task)
            await session.commit()

            embed = discord.Embed(
                title="タスク削除",
                description=f"タスク「{task.title}」を削除しました。",
                color=discord.Color.red(),
            )
            embed.add_field(name="削除者", value=interaction.user.mention, inline=True)
            embed.add_field(
                name="削除日時", value=datetime.utcnow().strftime("%Y-%m-%d %H:%M"), inline=True
            )

            await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot) -> None:
    """コグのセットアップ（ギルド限定コマンド同期）"""
    await bot.add_cog(TaskCog(bot))
    guild_id = settings.DISCORD_DEVELOPMENT_GUILD_ID
    if guild_id:
        guild = discord.Object(id=guild_id)
        await bot.tree.sync(guild=guild) 