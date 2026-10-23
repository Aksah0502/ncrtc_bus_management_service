from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.modules.fleet.models import Depot, Vehicle
from app.modules.users.models import User


class Incident(Base):
    __tablename__ = "incidents"

    __table_args__ = (
        CheckConstraint(
            "type IN ('breakdown', 'accident', 'complaint', 'other')",
            name="ck_incidents_type",
        ),
        CheckConstraint(
            "severity IN ('P1', 'P2', 'P3')",
            name="ck_incidents_severity",
        ),
        CheckConstraint(
            "status IN ('open', 'acknowledged', 'in_progress', "
            "'resolved', 'closed')",
            name="ck_incidents_status",
        ),
        Index("ix_incidents_depot_status", "depot_id", "status"),
        Index("ix_incidents_status_severity", "status", "severity"),
        Index("ix_incidents_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    incident_type: Mapped[str] = mapped_column(
        "type", String(30), nullable=False
    )

    severity: Mapped[str] = mapped_column(String(2), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="open",
        server_default="open",
    )

    raised_by: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    assigned_to: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    vehicle_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("vehicles.id", ondelete="RESTRICT"),
        nullable=True,
    )

    depot_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("depots.id", ondelete="RESTRICT"),
        nullable=False,
    )

    description: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    reporter: Mapped[User] = relationship(
        foreign_keys=[raised_by]
    )

    assignee: Mapped[User | None] = relationship(
        foreign_keys=[assigned_to]
    )

    vehicle: Mapped[Vehicle | None] = relationship()
    depot: Mapped[Depot] = relationship()


class IncidentEvent(Base):
    __tablename__ = "incident_events"

    __table_args__ = (
        CheckConstraint(
            "from_status IS NULL OR from_status IN "
            "('open', 'acknowledged', 'in_progress', 'resolved', 'closed')",
            name="ck_incident_events_from_status",
        ),
        CheckConstraint(
            "to_status IN "
            "('open', 'acknowledged', 'in_progress', 'resolved', 'closed')",
            name="ck_incident_events_to_status",
        ),
        Index("ix_incident_events_incident_ts", "incident_id", "ts"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    incident_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("incidents.id", ondelete="RESTRICT"),
        nullable=False,
    )

    ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    actor_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    from_status: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )

    to_status: Mapped[str] = mapped_column(
        String(20), nullable=False
    )

    note: Mapped[str] = mapped_column(Text, nullable=False)

    incident: Mapped["Incident"] = relationship()
    actor: Mapped["User"] = relationship()