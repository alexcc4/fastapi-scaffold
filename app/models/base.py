from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import BigInteger, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


SHANGHAI_TIMEZONE = ZoneInfo("Asia/Shanghai")


def get_local_now() -> datetime:
    return datetime.now(SHANGHAI_TIMEZONE).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class BigIntIdMixin:
    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=get_local_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=get_local_now,
        onupdate=get_local_now,
        nullable=False,
    )
