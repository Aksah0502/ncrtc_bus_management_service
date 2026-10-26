from datetime import datetime, time
from uuid import uuid4
from zoneinfo import ZoneInfo

from app.core.security import create_access_token, hash_password
from app.modules.fleet.models import Vehicle
from app.modules.routes.models import Route
from app.modules.scheduling.models import Duty
from app.modules.users.models import User


def test_live_details_returns_contact_fields_for_assigned_driver(
    client, db, test_users
):
    assigned_driver = test_users[1]
    suffix = uuid4().hex[:8]
    assigned_driver.phone = f"9{uuid4().int % 10**9:09d}"
    assigned_driver.driving_license_number = f"TEST-LIC-{suffix}"

    manager = User(
        username=f"test_live_details_manager_{suffix}",
        password_hash=hash_password("TestPass@123"),
        full_name="Live Details Test Manager",
        role="depot_manager",
        depot_id=assigned_driver.depot_id,
    )
    vehicle = Vehicle(
        reg_no=f"TEST-LIVE-{suffix}",
        depot_id=assigned_driver.depot_id,
        status="active",
    )
    route = Route(
        code=f"TEST-LIVE-{suffix}",
        name="Live Details Test Route",
        depot_id=assigned_driver.depot_id,
    )

    db.add_all([manager, vehicle, route])
    db.flush()
    duty = Duty(
        service_date=datetime.now(ZoneInfo("Asia/Kolkata")).date(),
        vehicle_id=vehicle.id,
        driver_id=assigned_driver.id,
        route_id=route.id,
        start_time=time(0),
        end_time=time(23, 59),
        status="published",
    )
    db.add(duty)
    db.commit()

    try:
        token = create_access_token(str(manager.id))
        response = client.get(
            f"/api/v1/vehicles/{vehicle.id}/live-details",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["vehicle_id"] == vehicle.id
        assert body["driver_name"] == assigned_driver.full_name
        assert body["driver_phone"] == assigned_driver.phone
        assert (
            body["driver_driving_license_number"]
            == assigned_driver.driving_license_number
        )
        assert body["route_name"] == route.name
    finally:
        db.delete(duty)
        db.delete(vehicle)
        db.delete(route)
        db.delete(manager)
        db.commit()
