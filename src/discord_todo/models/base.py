from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import MetaData
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# 命名規則の設定
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=convention)


def get_jst_now() -> datetime:
    """現在のJST時刻を取得"""
    return datetime.utcnow() + timedelta(hours=9)


class Base(DeclarativeBase):
    """全モデルの基底クラス"""

    metadata = metadata

    @declared_attr.directive
    def __tablename__(cls) -> str:
        """テーブル名をクラス名のスネークケースで生成"""
        return cls.__name__.lower()

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(default=get_jst_now)
    updated_at: Mapped[datetime] = mapped_column(
        default=get_jst_now, onupdate=get_jst_now
    )

    def dict(self) -> dict[str, Any]:
        """モデルをディクショナリに変換"""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        } 