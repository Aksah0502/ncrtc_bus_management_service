from datetime import date as DateType, time as TimeType, datetime

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Time,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.modules.fleet.models import Vehicle
from app.modules.routes.models import Route
from app.modules.users.models import User


class Duty(Base):
    __tablename__ = "duties"

    __table_args__ = (
        Index("ix_duties_date", "date"),
        Index("ix_duties_driver_date", "driver_id", "date"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    service_date: Mapped[DateType] = mapped_column(
        "date", Date, nullable=False
    )

    vehicle_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("vehicles.id", ondelete="RESTRICT"),
        nullable=False,
    )

    driver_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    conductor_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )

    route_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("routes.id", ondelete="RESTRICT"),
        nullable=False,
    )

    start_time: Mapped[TimeType] = mapped_column(Time, nullable=False)
    end_time: Mapped[TimeType] = mapped_column(Time, nullable=False)

    status: Mapped[str] = mapped_column(String(30), nullable=False)

    ack_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    vehicle: Mapped[Vehicle] = relationship()
    driver: Mapped[User] = relationship(foreign_keys=[driver_id])
    conductor: Mapped[User | None] = relationship(
        foreign_keys=[conductor_id]
    )
    route: Mapped[Route] = relationship()