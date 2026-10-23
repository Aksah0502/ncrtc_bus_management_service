from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Double,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.modules.fleet.models import Depot


class Stop(Base):
    __tablename__ = "stops"

    __table_args__ = (
        CheckConstraint(
            "lat BETWEEN -90 AND 90",
            name="ck_stops_latitude_range",
        ),
        CheckConstraint(
            "lng BETWEEN -180 AND 180",
            name="ck_stops_longitude_range",
        ),
        Index("ix_stops_name", "name"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    lat: Mapped[float] = mapped_column(Double, nullable=False)
    lng: Mapped[float] = mapped_column(Double, nullable=False)

    route_stops: Mapped[list[RouteStop]] = relationship(
        back_populates="stop",
        passive_deletes="all",
    )


class Route(Base):
    __tablename__ = "routes"

    __table_args__ = (
        Index("ix_routes_depot_id", "depot_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    depot_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("depots.id", ondelete="RESTRICT"),
        nullable=False,
    )

    depot: Mapped[Depot] = relationship()

    route_stops: Mapped[list[RouteStop]] = relationship(
        back_populates="route",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="RouteStop.sequence",
    )


class RouteStop(Base):
    __tablename__ = "route_stops"

    __table_args__ = (
        CheckConstraint(
            '"sequence" >= 1',
            name="ck_route_stops_sequence_positive",
        ),
        CheckConstraint(
            "planned_offset_min >= 0",
            name="ck_route_stops_offset_nonnegative",
        ),
        Index("ix_route_stops_stop_id", "stop_id"),
    )

    route_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("routes.id", ondelete="CASCADE"),
        primary_key=True,
    )

    sequence: Mapped[int] = mapped_column(
        "sequence",
        Integer,
        primary_key=True,
    )

    stop_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("stops.id", ondelete="RESTRICT"),
        nullable=False,
    )

    planned_offset_min: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    route: Mapped[Route] = relationship(back_populates="route_stops")
    stop: Mapped[Stop] = relationship(back_populates="route_stops")