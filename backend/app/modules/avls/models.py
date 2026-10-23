from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.modules.fleet.models import Vehicle


class GPSPing(Base):
    __tablename__ = "gps_pings"

    __table_args__ = (
        CheckConstraint(
            "lat BETWEEN -90 AND 90",
            name="ck_gps_pings_latitude_range",
        ),
        CheckConstraint(
            "lng BETWEEN -180 AND 180",
            name="ck_gps_pings_longitude_range",
        ),
        CheckConstraint(
            "speed_kmh IS NULL OR speed_kmh >= 0",
            name="ck_gps_pings_speed_nonnegative",
        ),
        Index("ix_gps_pings_vehicle_ts", "vehicle_id", "ts"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    vehicle_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("vehicles.id", ondelete="RESTRICT"),
        nullable=False,
    )

    ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)

    speed_kmh: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    ignition_on: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
    )

    vehicle: Mapped[Vehicle] = relationship()