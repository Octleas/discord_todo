from datetime import datetime
from enum import Enum
from typing import List

from sqlalchemy import String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class ImportanceLevel(str, Enum):
    """タスクの重要度"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TaskStatus(str, Enum):
    """タスクのステータス"""

    PENDING = "pending"
    COMPLETED = "completed"


class Task(Base):
    """タスクモデル"""

    guild_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    channel_id: Mapped[str] = mapped_column(String(255), nullable=False)
    message_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    assigned_to: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    deadline: Mapped[datetime] = mapped_column(nullable=False, index=True)
    importance: Mapped[ImportanceLevel] = mapped_column(default=ImportanceLevel.MEDIUM)
    status: Mapped[TaskStatus] = mapped_column(default=TaskStatus.PENDING, index=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    pdf_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    
    # 通知設定（分単位で保存）
    notification_times: Mapped[List[int]] = mapped_column(
        JSON, nullable=False, default=list
    )
    # 通知済みの時間（分単位で保存）
    notified_times: Mapped[List[int]] = mapped_column(
        JSON, nullable=False, default=list
    )

    @property
    def short_id(self) -> str:
        """3文字のショートID"""
        # IDを36進数に変換して3文字に制限
        return hex(self.id)[2:].zfill(3)[-3:] 