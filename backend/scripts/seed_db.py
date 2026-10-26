
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone

import bcrypt
from sqlalchemy import select

from app.db.session import SessionLocal
from app.modules.fleet.models import Depot, Vehicle
from app.modules.users.models import User
from app.modules.routes.models import Stop, Route, RouteStop
from app.modules.scheduling.models import Duty
from app.modules.avls.models import GPSPing
from app.modules.incidents.models import Incident, IncidentEvent
from app.modules.cms.models import Notice, NoticeRead


# Development-only credentials. Never reuse these in production.
SEED_PASSWORD = "DevOnly@123"
IST = timezone(timedelta(hours=5, minutes=30))

# Fictional demo identities and contact details. Do not use for real operations.
FIRST_NAMES = [
    "Rahul", "Amit", "Vikas", "Priya", "Rohit", "Neha", "Sandeep", "Pooja",
    "Arjun", "Anjali", "Deepak", "Kavita", "Manish", "Sneha", "Akash", "Ritu",
    "Nitin", "Meena", "Sanjay", "Aarti", "Mohit", "Simran", "Varun", "Shweta",
    "Karan", "Divya", "Gaurav", "Isha", "Ajay", "Nisha",
]
LAST_NAMES = [
    "Sharma", "Verma", "Yadav", "Singh", "Kumar", "Gupta", "Chauhan", "Mishra",
    "Mehta", "Kapoor", "Joshi", "Malhotra", "Arora", "Bansal", "Tyagi", "Rana",
    "Saxena", "Saini", "Rawat", "Agarwal",
]

DEPOT_SPECS = [
    ("SEED-D01", "Kashmere Gate", 28.6675, 77.2285),
    ("SEED-D02", "Anand Vihar", 28.6469, 77.3160),
    ("SEED-D03", "Ghaziabad", 28.6692, 77.4538),
    ("SEED-D04", "Pari Chowk", 28.4650, 77.5080),
    ("SEED-D05", "Noida Sector 52", 28.5850, 77.3680),
]

STOP_SPECS = [
    ("Kashmere Gate", 28.6675, 77.2285),
    ("ISBT Kashmere Gate", 28.6692, 77.2280),
    ("Civil Lines", 28.6773, 77.2250),
    ("Red Fort", 28.6562, 77.2410),
    ("ITO", 28.6289, 77.2405),
    ("Anand Vihar ISBT", 28.6469, 77.3160),
    ("Kaushambi", 28.6450, 77.3240),
    ("Vaishali", 28.6495, 77.3390),
    ("Ghaziabad Railway Station", 28.6692, 77.4538),
    ("Raj Nagar", 28.7010, 77.4350),
    ("Noida Sector 15", 28.5850, 77.3110),
    ("Noida Sector 18", 28.5708, 77.3260),
    ("Noida Sector 52", 28.5850, 77.3680),
    ("Noida City Centre", 28.5745, 77.3560),
    ("Botanical Garden", 28.5640, 77.3340),
    ("Pari Chowk", 28.4650, 77.5080),
    ("Alpha 1", 28.4720, 77.5030),
    ("Knowledge Park II", 28.4560, 77.5000),
    ("Rajiv Chowk Gurugram", 28.4595, 77.0266),
    ("IFFCO Chowk", 28.4722, 77.0720),
]

ROUTE_SPECS = [
    ("Kashmere Gate – Noida Sector 52", 0, 12),
    ("Anand Vihar – Ghaziabad", 5, 8),
    ("Pari Chowk – Noida Sector 18", 15, 11),
    ("Kashmere Gate – Anand Vihar", 0, 5),
    ("Ghaziabad – Noida Sector 52", 8, 12),
    ("Pari Chowk – Knowledge Park II", 15, 17),
    ("Noida Sector 52 – Botanical Garden", 12, 14),
    ("Anand Vihar – IFFCO Chowk", 5, 19),
    ("Kashmere Gate – ITO", 0, 4),
    ("Ghaziabad – Kaushambi", 8, 6),
    ("Noida Sector 15 – Pari Chowk", 10, 15),
    ("Raj Nagar – Anand Vihar", 9, 5),
]

# Plausible-format but fictional registration numbers; stable by vehicle index.
def registration_for(index: int) -> str:
    prefixes = ["DL01PC", "DL05AC", "DL10CG", "DL11CD", "UP14BT", "UP16CT"]
    return f"{prefixes[index % len(prefixes)]}{(index + 1):04d}"


def person_name(index: int) -> str:
    # 30 x 20 combinations gives unique names for the seeded population.
    return f"{FIRST_NAMES[index % len(FIRST_NAMES)]} {LAST_NAMES[(index // len(FIRST_NAMES) + index % 7) % len(LAST_NAMES)]}"

created_counts = {
    "depots": 0,
    "users": 0,
    "vehicles": 0,
    "stops": 0,
    "routes": 0,
    "route_stops": 0,
    "duties": 0,
    "gps_pings": 0,
    "incidents": 0,
    "incident_events": 0,
    "notices": 0,
    "notice_reads": 0,
}


def get_or_create(session, model, lookup: dict, values: dict, table: str):
    """Find a seed record by stable key, otherwise create it."""
    obj = session.scalar(
        select(model).filter_by(**lookup).limit(1)
    )
    if obj is not None:
        for field, value in values.items():
            # Preserve existing login passwords when refreshing demo profile data.
            if field == "password_hash":
                continue
            setattr(obj, field, value)
        session.flush()
        return obj

    obj = model(**values)
    session.add(obj)
    session.flush()
    created_counts[table] += 1
    return obj


def make_password_hash(password: str) -> str:
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")


def seed_database() -> None:
    if not hasattr(User, "driving_license_number"):
        raise RuntimeError(
            "User.driving_license_number is missing. Add the model field and apply its Alembic migration before seeding."
        )

    today = datetime.now(IST).date()
    historical_day = today - timedelta(days=1)
    week_start = today - timedelta(days=today.weekday())
    password_hash = make_password_hash(SEED_PASSWORD)

    # All work happens in one transaction. If any step raises an error,
    # SQLAlchemy rolls back the transaction when the context exits.
    with SessionLocal() as session:
        with session.begin():
            # ---------------------------------------------------------
            # 1. Depots
            # ---------------------------------------------------------
            depot_specs = DEPOT_SPECS

            depots = []
            for code, name, lat, lng in depot_specs:
                depots.append(
                    get_or_create(
                        session,
                        Depot,
                        {"code": code},
                        {
                            "code": code,
                            "name": name,
                            "location_lat": lat,
                            "location_lng": lng,
                            "boundary_geom": None,
                        },
                        "depots",
                    )
                )

            # ---------------------------------------------------------
            # 2. Users: 60 drivers, 10 managers, 8 operators, 2 admins
            # ---------------------------------------------------------
            drivers = []
            managers = []
            operators = []
            admins = []
            phone_number = 9000000001

            for i in range(60):
                depot = depots[i % len(depots)]
                user = get_or_create(
                    session,
                    User,
                    {"username": f"seed_driver_{i + 1:03d}"},
                    {
                        "username": f"seed_driver_{i + 1:03d}",
                        "password_hash": password_hash,
                        "full_name": person_name(i),
                        "role": "driver",
                        "depot_id": depot.id,
                        "phone": str(phone_number),
                        "driving_license_number": f"DL-DEL-DEMO-{i + 1:04d}",
                    },
                    "users",
                )
                drivers.append(user)
                phone_number += 1

            for i in range(10):
                depot = depots[i % len(depots)]
                user = get_or_create(
                    session,
                    User,
                    {"username": f"seed_manager_{i + 1:03d}"},
                    {
                        "username": f"seed_manager_{i + 1:03d}",
                        "password_hash": password_hash,
                        "full_name": person_name(60 + i),
                        "role": "depot_manager",
                        "depot_id": depot.id,
                        "phone": str(phone_number),
                    },
                    "users",
                )
                managers.append(user)
                phone_number += 1

            for i in range(8):
                user = get_or_create(
                    session,
                    User,
                    {"username": f"seed_operator_{i + 1:03d}"},
                    {
                        "username": f"seed_operator_{i + 1:03d}",
                        "password_hash": password_hash,
                        "full_name": person_name(70 + i),
                        "role": "control_operator",
                        "depot_id": None,
                        "phone": str(phone_number),
                    },
                    "users",
                )
                operators.append(user)
                phone_number += 1

            for i in range(2):
                user = get_or_create(
                    session,
                    User,
                    {"username": f"seed_admin_{i + 1:03d}"},
                    {
                        "username": f"seed_admin_{i + 1:03d}",
                        "password_hash": password_hash,
                        "full_name": person_name(80 + i),
                        "role": "admin",
                        "depot_id": None,
                        "phone": str(phone_number),
                    },
                    "users",
                )
                admins.append(user)
                phone_number += 1

            drivers_by_depot = defaultdict(list)
            managers_by_depot = defaultdict(list)
            for user in drivers:
                if user.depot_id is not None:
                    drivers_by_depot[user.depot_id].append(user)
            for user in managers:
                if user.depot_id is not None:
                    managers_by_depot[user.depot_id].append(user)

            # ---------------------------------------------------------
            # 3. Vehicles: 50
            # ---------------------------------------------------------
            vehicles = []
            vehicles_by_depot = defaultdict(list)

            for i in range(50):
                depot = depots[i % len(depots)]
                legacy_reg_no = f"SEED-BUS-{i + 1:03d}"
                reg_no = registration_for(i)
                status = "maintenance" if (i + 1) % 13 == 0 else "active"

                # Match either the legacy seed registration or the new stable one,
                # so rerunning this script updates rather than duplicates vehicles.
                vehicle = session.scalar(
                    select(Vehicle).where(
                        Vehicle.reg_no.in_([legacy_reg_no, reg_no])
                    ).limit(1)
                )
                if vehicle is None:
                    vehicle = Vehicle(
                        reg_no=reg_no, depot_id=depot.id, status=status
                    )
                    session.add(vehicle)
                    session.flush()
                    created_counts["vehicles"] += 1
                else:
                    vehicle.reg_no = reg_no
                    vehicle.depot_id = depot.id
                    vehicle.status = status
                    session.flush()
                vehicles.append(vehicle)
                vehicles_by_depot[vehicle.depot_id].append(vehicle)

            depot_by_id = {depot.id: depot for depot in depots}

            # ---------------------------------------------------------
            # 4. Stops: 20 fictional points
            # ---------------------------------------------------------
            stops = []
            for i, (name, lat, lng) in enumerate(STOP_SPECS):
                legacy_name = f"Sample Stop {i + 1:02d}"
                stop = session.scalar(
                    select(Stop).where(Stop.name.in_([legacy_name, name])).limit(1)
                )
                if stop is None:
                    stop = Stop(name=name, lat=lat, lng=lng)
                    session.add(stop)
                    session.flush()
                    created_counts["stops"] += 1
                else:
                    stop.name = name
                    stop.lat = lat
                    stop.lng = lng
                    session.flush()
                stops.append(stop)

            # ---------------------------------------------------------
            # 5. Routes: 12, allocated to depots
            # ---------------------------------------------------------
            routes = []
            routes_by_depot = defaultdict(list)

            for i, (route_name, start_stop_index, end_stop_index) in enumerate(ROUTE_SPECS):
                depot = depots[i % len(depots)]
                code = f"SEED-R{i + 1:03d}"

                route = get_or_create(
                    session,
                    Route,
                    {"code": code},
                    {
                        "code": code,
                        "name": route_name,
                        "depot_id": depot.id,
                    },
                    "routes",
                )
                routes.append(route)
                routes_by_depot[route.depot_id].append(route)

                # Five ordered stops, with route-name endpoints matching actual stops.
                intermediate = [
                    (start_stop_index + 1) % len(stops),
                    (start_stop_index + 2) % len(stops),
                    (end_stop_index - 1) % len(stops),
                ]
                stop_indices = [start_stop_index, *intermediate, end_stop_index]
                for sequence, stop_index in enumerate(stop_indices, start=1):
                    stop = stops[stop_index]

                    get_or_create(
                        session,
                        RouteStop,
                        {"route_id": route.id, "sequence": sequence},
                        {
                            "route_id": route.id,
                            "sequence": sequence,
                            "stop_id": stop.id,
                            "planned_offset_min": (sequence - 1) * 15,
                        },
                        "route_stops",
                    )

            # ---------------------------------------------------------
            # 6. Duties: every vehicle scheduled each day of this week
            # ---------------------------------------------------------
            for day_offset in range(7):
                service_date = week_start + timedelta(days=day_offset)

                for depot in depots:
                    depot_vehicles = vehicles_by_depot[depot.id]
                    depot_drivers = drivers_by_depot[depot.id]
                    depot_routes = routes_by_depot[depot.id]

                    for local_index, vehicle in enumerate(depot_vehicles):
                        driver = depot_drivers[
                            (local_index + day_offset) % len(depot_drivers)
                        ]
                        route = depot_routes[
                            (local_index + day_offset) % len(depot_routes)
                        ]

                        start_dt = datetime.combine(
                            service_date, time(6, 0), tzinfo=IST
                        ) + timedelta(minutes=(local_index % 6) * 15)
                        end_dt = start_dt + timedelta(hours=8)

                        ack_at = None
                        if service_date <= today and (
                            local_index + day_offset
                        ) % 3 != 0:
                            ack_at = start_dt - timedelta(minutes=30)

                        get_or_create(
                            session,
                            Duty,
                            {
                                "service_date": service_date,
                                "vehicle_id": vehicle.id,
                                "start_time": start_dt.time(),
                            },
                            {
                                "service_date": service_date,
                                "vehicle_id": vehicle.id,
                                "driver_id": driver.id,
                                "conductor_id": None,
                                "route_id": route.id,
                                "start_time": start_dt.time(),
                                "end_time": end_dt.time(),
                                "status": "published",
                                "ack_at": ack_at,
                            },
                            "duties",
                        )

            # ---------------------------------------------------------
            # 7. GPS history: 15 vehicles x 12 pings = 180 points
            # ---------------------------------------------------------
            gps_start = datetime.combine(historical_day, time(4, 0), tzinfo=IST)

            for vehicle_index, vehicle in enumerate(vehicles[:15]):
                depot = depot_by_id[vehicle.depot_id]

                for point_index in range(12):
                    ts = gps_start + timedelta(minutes=point_index * 5)
                    lat = depot.location_lat + (vehicle_index % 4) * 0.001
                    lng = depot.location_lng + (vehicle_index % 4) * 0.001
                    lat += point_index * 0.001
                    lng += point_index * 0.001

                    get_or_create(
                        session,
                        GPSPing,
                        {"vehicle_id": vehicle.id, "ts": ts},
                        {
                            "vehicle_id": vehicle.id,
                            "ts": ts,
                            "lat": lat,
                            "lng": lng,
                            "speed_kmh": float(18 + point_index),
                            "ignition_on": True,
                        },
                        "gps_pings",
                    )

            # ---------------------------------------------------------
            # 8. Incidents and incident event histories
            # ---------------------------------------------------------
            incident_specs = [
                ("breakdown", "P1", "open", "Vehicle reported a breakdown"),
                ("accident", "P1", "acknowledged", "Road accident reported"),
                ("complaint", "P2", "in_progress", "Passenger complaint recorded"),
                ("other", "P2", "resolved", "Operational issue resolved"),
                ("breakdown", "P3", "closed", "Minor vehicle issue closed"),
                ("complaint", "P2", "open", "Service complaint awaiting review"),
            ]

            status_path = [
                "open",
                "acknowledged",
                "in_progress",
                "resolved",
                "closed",
            ]

            for i, (kind, severity, final_status, summary) in enumerate(
                incident_specs
            ):
                depot = depots[i % len(depots)]
                depot_drivers = drivers_by_depot[depot.id]
                depot_vehicles = vehicles_by_depot[depot.id]
                depot_managers = managers_by_depot[depot.id]

                reporter = depot_drivers[i % len(depot_drivers)]
                vehicle = None if i == 2 else depot_vehicles[i % len(depot_vehicles)]
                assignee = (
                    None if final_status == "open"
                    else depot_managers[0]
                )

                description = f"SEED-INC-{i + 1:03d}: {summary}"
                created_at = datetime.combine(
                    historical_day, time(9, 0), tzinfo=IST
                ) + timedelta(minutes=i * 30)

                incident = get_or_create(
                    session,
                    Incident,
                    {"description": description},
                    {
                        "incident_type": kind,
                        "severity": severity,
                        "status": final_status,
                        "raised_by": reporter.id,
                        "assigned_to": assignee.id if assignee else None,
                        "vehicle_id": vehicle.id if vehicle else None,
                        "depot_id": depot.id,
                        "description": description,
                        "created_at": created_at,
                        "resolved_at": (
                            created_at + timedelta(minutes=60)
                            if final_status in ("resolved", "closed")
                            else None
                        ),
                    },
                    "incidents",
                )

                last_status_index = status_path.index(incident.status)
                for step, to_status in enumerate(
                    status_path[: last_status_index + 1]
                ):
                    from_status = None if step == 0 else status_path[step - 1]
                    actor = reporter if step == 0 else (assignee or reporter)
                    event_ts = incident.created_at + timedelta(
                        minutes=step * 10
                    )
                    note = f"Seed event: status set to {to_status}"

                    get_or_create(
                        session,
                        IncidentEvent,
                        {
                            "incident_id": incident.id,
                            "ts": event_ts,
                            "to_status": to_status,
                        },
                        {
                            "incident_id": incident.id,
                            "ts": event_ts,
                            "actor_id": actor.id,
                            "from_status": from_status,
                            "to_status": to_status,
                            "note": note,
                        },
                        "incident_events",
                    )

            # ---------------------------------------------------------
            # 9. Notices and read receipts
            # ---------------------------------------------------------
            publish_at = datetime.combine(
                historical_day, time(7, 0), tzinfo=IST
            )

            notice_specs = [
                (
                    "SEED-NOTICE-001",
                    "Sample general service notice",
                    "This is a fictional general operational notice.",
                    {"type": "all"},
                ),
                (
                    "SEED-NOTICE-002",
                    "Sample driver reminder",
                    "Review your published duty before beginning the shift.",
                    {"roles": ["driver"]},
                ),
                (
                    "SEED-NOTICE-003",
                    "Sample depot maintenance notice",
                    "A maintenance notice for the Kashmere Gate operating area (demo data).",
                    {"depot_ids": [depots[0].id]},
                ),
                (
                    "SEED-NOTICE-004",
                    "Sample operations update",
                    "A fictional update for managers and control operators.",
                    {"roles": ["depot_manager", "control_operator"]},
                ),
            ]

            notices = []
            for title, body_title, body, audience in notice_specs:
                notice = get_or_create(
                    session,
                    Notice,
                    {"title": title},
                    {
                        "title": title,
                        "body": f"{body_title}\n\n{body}",
                        "audience_json": audience,
                        "publish_at": publish_at,
                        "created_by": admins[0].id,
                    },
                    "notices",
                )
                notices.append(notice)

            read_pairs = []
            read_pairs.extend((notices[0], user) for user in drivers[:15])
            read_pairs.extend((notices[1], user) for user in drivers[15:25])
            read_pairs.extend(
                (notices[2], user)
                for user in (
                    drivers_by_depot[depots[0].id][:3]
                    + managers_by_depot[depots[0].id][:1]
                )
            )

            for notice, user in read_pairs:
                key = {
                    "notice_id": notice.id,
                    "user_id": user.id,
                }
                if session.get(NoticeRead, key) is None:
                    session.add(
                        NoticeRead(
                            **key,
                            read_at=notice.publish_at + timedelta(minutes=30),
                        )
                    )
                    session.flush()
                    created_counts["notice_reads"] += 1

    # Print only after the transaction has committed successfully.
    print("\nSeed completed successfully.")
    print("New records created during this run:")
    for table, count in created_counts.items():
        print(f"  {table}: {count}")

    print("\nSeed login:")
    print("  Username: seed_admin_001")
    print(f"  Password: {SEED_PASSWORD}")
    print("  Development only; never use this password in production.")
    print("  Existing usernames are preserved; existing password hashes are not overwritten.")


if __name__ == "__main__":
    seed_database()
