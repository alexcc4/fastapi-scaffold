from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, BigIntIdMixin, TimestampMixin


class User(BigIntIdMixin, TimestampMixin, Base):
    __tablename__ = "users"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    session_version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        server_default=text("1"),
        nullable=False,
    )


class AuthUser(BigIntIdMixin, TimestampMixin, Base):
    __tablename__ = "auth_users"
    __table_args__ = (
        UniqueConstraint(
            "auth_id",
            name="uq_auth_users_auth_id",
        ),
        UniqueConstraint(
            "user_id",
            name="uq_auth_users_user_id",
        ),
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )
    auth_id: Mapped[str] = mapped_column(String(64), nullable=False)
    credential: Mapped[str] = mapped_column(String(60), nullable=False)
