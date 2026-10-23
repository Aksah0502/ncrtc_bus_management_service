from __future__ import annotations

from typing import TYPE_CHECKING

from geoalchemy2 import Geometry
from geoalchemy2.elements import WKBElement
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Float,
    ForeignKey,
    Index,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.modules.users.models import User


class Depot(Base):
    __tablename__ = "depots"

    __table_args__ = (
        CheckConstraint(
            "location_lat >= -90 AND location_lat <= 90",
            name="ck_depots_latitude_range",
        ),
        CheckConstraint(
            "location_lng >= -180 AND location_lng <= 180",
            name="ck_depots_longitude_range",
        ),
        Index(
            "idx_depots_boundary_geom",
            "boundary_geom",
            postgresql_using="gist",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    location_lat: Mapped[float] = mapped_column(Float, nullable=False)
    location_lng: Mapped[float] = mapped_column(Float, nullable=False)

    boundary_geom: Mapped[WKBElement | None] = mapped_column(
        Geometry(
            geometry_type="MULTIPOLYGON",
            srid=4326,
            spatial_index=False,
        ),
        nullable=True,
    )

    vehicles: Mapped[list[Vehicle]] = relationship(
        back_populates="depot",
        passive_deletes="all",
    )

    users: Mapped[list["User"]] = relationship(
        "User",
        back_populates="depot",
        passive_deletes=True,
    )


class Vehicle(Base):
    __tablename__ = "vehicles"

    __table_args__ = (
        Index("ix_vehicles_depot_status", "depot_id", "status"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    reg_no: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)

    depot_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("depots.id", ondelete="RESTRICT"),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(String(30), nullable=False)

    depot: Mapped[Depot] = relationship(back_populates="vehicles")