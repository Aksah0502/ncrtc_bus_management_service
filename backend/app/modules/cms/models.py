from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.modules.users.models import User


class Notice(Base):
    __tablename__ = "notices"

    __table_args__ = (
        Index("ix_notices_publish_at", "publish_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)

    audience_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
    )

    publish_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    created_by: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    author: Mapped[User] = relationship()
    read_receipts: Mapped[list["NoticeRead"]] = relationship(
        back_populates="notice",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class NoticeRead(Base):
    __tablename__ = "notice_reads"

    __table_args__ = (
        Index("ix_notice_reads_user_id", "user_id"),
    )

    notice_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("notices.id", ondelete="CASCADE"),
        primary_key=True,
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )

    read_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    notice: Mapped[Notice] = relationship(back_populates="read_receipts")
    user: Mapped[User] = relationship()