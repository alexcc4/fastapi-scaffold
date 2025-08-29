from datetime import datetime

from sqlalchemy import String, BigInteger, SmallInteger, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.mysql import JSON

from app.models.base import Base


class User(Base):
    __tablename__ = "user"
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_url: Mapped[str] = mapped_column(String(255), nullable=True)
    
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1, server_default="1")
    is_verified: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0, server_default="0")
    deleted_at: Mapped[datetime] = mapped_column(DateTime, nullable=True, index=True)


class AuthUser(Base):
    __tablename__ = "auth_user"
    
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    auth_id: Mapped[str] = mapped_column(String(255), nullable=False)
    auth_type: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    credential: Mapped[str] = mapped_column(String(255), nullable=True)

    auth_data: Mapped[dict] = mapped_column(JSON, nullable=True, comment="additional payload")
    last_login_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint("auth_id", "auth_type", name="uix_auth_id_auth_type"),
    )