
import argparse
import logging
from datetime import datetime
from random import uniform
from threading import Event
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.db.session import SessionLocal
from app.modules.avls.models import GPSPing
from app.modules.fleet.models import Vehicle
from app.modules.routes.models import RouteStop, Stop
from app.modules.scheduling.models import Duty

IST = ZoneInfo("Asia/Kolkata")
logger = logging.getLogger(__name__)


def load_active_trips(db, today):
    assignments = db.execute(
        select(Vehicle.id, Duty.route_id)
        .join(Duty, Duty.vehicle_id == Vehicle.id)
        .where(
            Vehicle.status == "active",
            Duty.service_date == today,
            Duty.status == "published",
        )
    ).all()

    if not assignments:
        return []

    route_ids = {route_id for _, route_id in assignments}

    stop_rows = db.execute(
        select(RouteStop.route_id, Stop.lat, Stop.lng)
        .join(Stop, Stop.id == RouteStop.stop_id)
        .where(RouteStop.route_id.in_(route_ids))
        .order_by(RouteStop.route_id, RouteStop.sequence)
    ).all()

    points_by_route = {}
    for route_id, lat, lng in stop_rows:
        points_by_route.setdefault(route_id, []).append((lat, lng))

    trips = []
    seen_vehicles = set()

    for vehicle_id, route_id in assignments:
        points = points_by_route.get(route_id, [])
        if vehicle_id not in seen_vehicles and len(points) >= 2:
            trips.append({"vehicle_id": vehicle_id, "points": points})
            seen_vehicles.add(vehicle_id)

    return trips


def interpolate(points, position):
    segment = min(int(position), len(points) - 2)
    fraction = position - segment
    lat1, lng1 = points[segment]
    lat2, lng2 = points[segment + 1]

    return (
        lat1 + (lat2 - lat1) * fraction,
        lng1 + (lng2 - lng1) * fraction,
    )


def run_simulator(stop_event: Event, interval: float = 5.0):
    positions = {}

    while not stop_event.is_set():
        now = datetime.now(IST)

        try:
            with SessionLocal() as db:
                trips = load_active_trips(db, now.date())

                for trip in trips:
                    vehicle_id = trip["vehicle_id"]
                    points = trip["points"]

                    position = positions.get(vehicle_id, 0.0)
                    lat, lng = interpolate(points, position)

                    db.add(
                        GPSPing(
                            vehicle_id=vehicle_id,
                            ts=now,
                            lat=lat + uniform(-0.00003, 0.00003),
                            lng=lng + uniform(-0.00003, 0.00003),
                            speed_kmh=round(uniform(15, 40), 1),
                            ignition_on=True,
                        )
                    )

                    next_position = position + 0.02
                    if next_position >= len(points) - 1:
                        next_position = 0.0
                    positions[vehicle_id] = next_position

                db.commit()
                print(
                    f"{now.isoformat()} | GPS pings inserted: {len(trips)}",
                    flush=True,
                )

        except Exception:
            logger.exception("GPS simulator tick failed")

        stop_event.wait(interval)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval", type=float, default=5.0)
    args = parser.parse_args()

    if args.interval < 1:
        parser.error("--interval must be at least 1 second")

    stop_event = Event()
    try:
        run_simulator(stop_event, args.interval)
    except KeyboardInterrupt:
        stop_event.set()
        print("GPS simulator stopped.", flush=True)


if __name__ == "__main__":
    main()
