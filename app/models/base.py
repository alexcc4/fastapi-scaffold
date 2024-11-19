from datetime import datetime, timezone

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import DateTime, BigInteger


def get_utc_now():
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=get_utc_now, nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=get_utc_now, onupdate=get_utc_now, nullable=False, index=True)