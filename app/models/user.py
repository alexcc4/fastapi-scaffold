from sqlalchemy import String, SmallInteger
from app.models.base import Base
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional


class User(Base):
    __tablename__ = "user"

    clerk_id: Mapped[str] = mapped_column(String(255), index=True, comment="clerk unique id")
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[int] = mapped_column(SmallInteger, default=1)
