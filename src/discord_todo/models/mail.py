from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class MailConnection(Base):
    """メール連携設定モデル"""

    guild_id: Mapped[str] = mapped_column(String(255), nullable=False)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    access_token: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token: Mapped[str] = mapped_column(Text, nullable=False)
    token_expires_at: Mapped[datetime] = mapped_column(nullable=False, index=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # リレーションシップ
    notifications: Mapped[list["MailNotification"]] = relationship(
        back_populates="connection", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("guild_id", "user_id", name="uq_mail_connection_guild_user"),
    )


class MailNotification(Base):
    """メール通知履歴モデル"""

    connection_id: Mapped[int] = mapped_column(ForeignKey("mailconnection.id"), nullable=False)
    message_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    sender: Mapped[str] = mapped_column(String(255), nullable=False)
    received_at: Mapped[datetime] = mapped_column(nullable=False, index=True)
    notified_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    discord_message_id: Mapped[str] = mapped_column(String(255), nullable=False)

    # リレーションシップ
    connection: Mapped[MailConnection] = relationship(back_populates="notifications") 