from __future__ import annotations

from sqlalchemy import BigInteger, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.modules.fleet.models import Depot


class User(Base):
    __tablename__ = "users"

    __table_args__ = (
        Index("ix_users_depot_id", "depot_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    role: Mapped[str] = mapped_column(String(30), nullable=False)

    depot_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("depots.id", ondelete="SET NULL"),
        nullable=True,
    )

    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)

    driving_license_number: Mapped[str | None] = mapped_column(
        String(30),
        unique=True,
        nullable=True,
    )

    depot: Mapped[Depot | None] = relationship(back_populates="users")