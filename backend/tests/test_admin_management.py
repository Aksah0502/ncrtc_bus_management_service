from datetime import date, datetime, time, timezone
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.security import create_access_token, hash_password, verify_password
from app.modules.avls.models import GPSPing
from app.modules.cms.models import Notice, NoticeRead
from app.modules.fleet.models import Depot, Vehicle
from app.modules.incidents.models import Incident, IncidentEvent
from app.modules.routes.models import Route, Stop
from app.modules.scheduling.models import Duty
from app.modules.users.models import User


def token_headers(user):
    return {"Authorization": f"Bearer {create_access_token(str(user.id))}"}


def key():
    return uuid4().hex[:8].upper()


def add_depot(db, suffix=None):
    suffix = suffix or key()
    depot = Depot(
        code=f"T-{suffix}",
        name=f"Admin Test Depot {suffix}",
        location_lat=28.6,
        location_lng=77.2,
    )
    db.add(depot)
    db.commit()
    db.refresh(depot)
    return depot


def add_user(db, role, depot_id=None, suffix=None, **fields):
    suffix = suffix or key()
    user = User(
        username=f"admin_test_{suffix.lower()}",
        password_hash=hash_password("SafeTestPass@1"),
        full_name=f"Admin Test {suffix}",
        role=role,
        depot_id=depot_id,
        **fields,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def delete_rows(db, *rows):
    for row in rows:
        if row is not None:
            db.delete(row)
    db.commit()


def test_vehicle_create_delete_admin_and_reject_non_admin(client, db, test_users):
    admin, driver = test_users
    depot = add_depot(db)
    payload = {
        "reg_no": f"V-{key()}",
        "depot_id": depot.id,
        "status": "active",
    }

    denied = client.post(
        "/api/v1/fleet/vehicles",
        headers=token_headers(driver),
        json=payload,
    )
    assert denied.status_code == 403

    created = client.post(
        "/api/v1/fleet/vehicles",
        headers=token_headers(admin),
        json=payload,
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["reg_no"] == payload["reg_no"]
    assert body["depot_id"] == depot.id
    assert "id" in body

    denied_delete = client.delete(
        f"/api/v1/fleet/vehicles/{body['id']}",
        headers=token_headers(driver),
    )
    assert denied_delete.status_code == 403

    deleted = client.delete(
        f"/api/v1/fleet/vehicles/{body['id']}",
        headers=token_headers(admin),
    )
    assert deleted.status_code == 204
    assert db.get(Vehicle, body["id"]) is None
    delete_rows(db, depot)


def test_vehicle_duplicate_registration_returns_conflict(client, db, test_users):
    admin = test_users[0]
    depot = add_depot(db)
    payload = {"reg_no": f"V-{key()}", "depot_id": depot.id, "status": "active"}
    first = client.post("/api/v1/fleet/vehicles", headers=token_headers(admin), json=payload)
    assert first.status_code == 201, first.text
    duplicate = client.post("/api/v1/fleet/vehicles", headers=token_headers(admin), json=payload)
    assert duplicate.status_code == 409
    delete_rows(db, db.get(Vehicle, first.json()["id"]), depot)


def test_vehicle_delete_preserves_gps_history_and_returns_conflict(
    client, db, test_users
):
    admin = test_users[0]
    depot = add_depot(db)
    vehicle = Vehicle(reg_no=f"V-{key()}", depot_id=depot.id, status="active")
    db.add(vehicle)
    db.flush()
    ping = GPSPing(
        vehicle_id=vehicle.id,
        ts=datetime.now(timezone.utc),
        lat=28.6,
        lng=77.2,
        speed_kmh=0,
        ignition_on=False,
    )
    db.add(ping)
    db.commit()
    vehicle_id, ping_id = vehicle.id, ping.id

    response = client.delete(
        f"/api/v1/fleet/vehicles/{vehicle_id}",
        headers=token_headers(admin),
    )
    assert response.status_code == 409
    assert db.get(Vehicle, vehicle_id) is not None
    assert db.get(GPSPing, ping_id) is not None
    delete_rows(db, db.get(GPSPing, ping_id), db.get(Vehicle, vehicle_id), depot)


def test_depot_create_assigns_unassigned_manager_atomically(client, db, test_users):
    admin = test_users[0]
    manager = add_user(db, "depot_manager")
    code = f"D-{key()}"
    payload = {
        "code": code,
        "name": "New Admin Depot",
        "location_lat": 28.61,
        "location_lng": 77.21,
        "depot_manager_id": manager.id,
    }

    response = client.post("/api/v1/fleet/depots", headers=token_headers(admin), json=payload)
    assert response.status_code == 201, response.text
    depot = db.get(Depot, response.json()["id"])
    db.refresh(manager)
    assert depot.code == code
    assert manager.depot_id == depot.id

    manager.depot_id = None
    db.commit()
    delete_rows(db, manager, depot)


def test_depot_create_rejects_invalid_manager(client, db, test_users):
    admin, driver = test_users
    code = f"D-{key()}"
    payload = {
        "code": code,
        "name": "Invalid Assignment Depot",
        "location_lat": 28.6,
        "location_lng": 77.2,
        "depot_manager_id": driver.id,
    }
    denied = client.post("/api/v1/fleet/depots", headers=token_headers(driver), json=payload)
    assert denied.status_code == 403
    response = client.post("/api/v1/fleet/depots", headers=token_headers(admin), json=payload)
    assert response.status_code == 422
    assert db.query(Depot).filter_by(code=code).first() is None


def test_depot_create_rejects_manager_already_assigned(client, db, test_users):
    admin = test_users[0]
    existing_depot = add_depot(db)
    manager = add_user(db, "depot_manager", depot_id=existing_depot.id)
    code = f"D-{key()}"
    response = client.post(
        "/api/v1/fleet/depots",
        headers=token_headers(admin),
        json={
            "code": code,
            "name": "Already Assigned Depot",
            "location_lat": 28.6,
            "location_lng": 77.2,
            "depot_manager_id": manager.id,
        },
    )
    assert response.status_code == 422
    assert db.query(Depot).filter_by(code=code).first() is None
    delete_rows(db, manager, existing_depot)


def test_depot_duplicate_code_keeps_second_manager_unassigned(
    client, db, test_users
):
    admin = test_users[0]
    first_manager = add_user(db, "depot_manager")
    second_manager = add_user(db, "depot_manager")
    code = f"D-{key()}"
    payload = {
        "code": code,
        "name": "Duplicate Depot",
        "location_lat": 28.6,
        "location_lng": 77.2,
        "depot_manager_id": first_manager.id,
    }
    first = client.post("/api/v1/fleet/depots", headers=token_headers(admin), json=payload)
    assert first.status_code == 201, first.text
    payload["depot_manager_id"] = second_manager.id
    duplicate = client.post("/api/v1/fleet/depots", headers=token_headers(admin), json=payload)
    assert duplicate.status_code == 409
    db.refresh(second_manager)
    assert second_manager.depot_id is None

    first_manager.depot_id = None
    db.commit()
    delete_rows(db, first_manager, second_manager, db.get(Depot, first.json()["id"]))


def test_depot_create_rolls_back_manager_assignment_on_commit_failure(
    client, db, test_users, monkeypatch
):
    admin = test_users[0]
    manager = add_user(db, "depot_manager")
    code = f"D-{key()}"

    def fail_commit():
        raise IntegrityError("forced failure", {}, RuntimeError("test failure"))

    with monkeypatch.context() as patch:
        patch.setattr(db, "commit", fail_commit)
        response = client.post(
            "/api/v1/fleet/depots",
            headers=token_headers(admin),
            json={
                "code": code,
                "name": "Atomic Depot",
                "location_lat": 28.6,
                "location_lng": 77.2,
                "depot_manager_id": manager.id,
            },
        )

    assert response.status_code == 409
    assert db.query(Depot).filter_by(code=code).first() is None
    db.refresh(manager)
    assert manager.depot_id is None
    delete_rows(db, manager)


def test_depot_delete_and_admin_only_access(client, db, test_users):
    admin, driver = test_users
    depot = add_depot(db)
    denied = client.delete(
        f"/api/v1/fleet/depots/{depot.id}",
        headers=token_headers(driver),
    )
    assert denied.status_code == 403
    deleted = client.delete(
        f"/api/v1/fleet/depots/{depot.id}",
        headers=token_headers(admin),
    )
    assert deleted.status_code == 204
    assert db.get(Depot, depot.id) is None


def test_depot_delete_preserves_vehicle_and_returns_conflict(client, db, test_users):
    admin = test_users[0]
    depot = add_depot(db)
    vehicle = Vehicle(reg_no=f"V-{key()}", depot_id=depot.id, status="active")
    db.add(vehicle)
    db.commit()
    depot_id, vehicle_id = depot.id, vehicle.id

    response = client.delete(
        f"/api/v1/fleet/depots/{depot_id}",
        headers=token_headers(admin),
    )
    assert response.status_code == 409
    assert db.get(Depot, depot_id) is not None
    assert db.get(Vehicle, vehicle_id) is not None
    delete_rows(db, db.get(Vehicle, vehicle_id), db.get(Depot, depot_id))


@pytest.mark.parametrize(
    ("role", "depot_assignment"),
    [("driver", "depot"), ("control_operator", None), ("depot_manager", None)],
)
def test_user_create_hashes_password_and_returns_safe_fields(
    client, db, test_users, role, depot_assignment
):
    admin = test_users[0]
    depot = add_depot(db) if depot_assignment == "depot" else None
    password = "AdminCreatePass@1"
    payload = {
        "username": f"new_user_{key().lower()}",
        "full_name": "New Managed User",
        "password": password,
        "role": role,
        "depot_id": depot.id if depot else None,
        "phone": "9876543210",
        "driving_license_number": f"LIC-{key()}",
    }
    response = client.post("/api/v1/users", headers=token_headers(admin), json=payload)
    assert response.status_code == 201, response.text
    body = response.json()
    user = db.get(User, body["id"])
    assert body["role"] == role
    assert body["phone"] == payload["phone"]
    assert body["driving_license_number"] == payload["driving_license_number"]
    assert "password_hash" not in body
    assert "password" not in body
    assert user.password_hash != password
    assert verify_password(password, user.password_hash)
    if role == "depot_manager" and depot is None:
        assert user.depot_id is None

    deleted = client.delete(f"/api/v1/users/{user.id}", headers=token_headers(admin))
    assert deleted.status_code == 204
    if depot:
        delete_rows(db, depot)


def test_user_create_rejects_admin_role_and_incompatible_depot(client, test_users):
    admin = test_users[0]
    base = {
        "username": f"bad_user_{key().lower()}",
        "full_name": "Invalid User",
        "password": "ValidPass@123",
    }
    admin_role = client.post(
        "/api/v1/users",
        headers=token_headers(admin),
        json={**base, "role": "admin"},
    )
    assert admin_role.status_code == 422

    operator_depot = client.post(
        "/api/v1/users",
        headers=token_headers(admin),
        json={**base, "username": base["username"] + "_2", "role": "control_operator", "depot_id": test_users[0].depot_id},
    )
    assert operator_depot.status_code == 422

    driver_without_depot = client.post(
        "/api/v1/users",
        headers=token_headers(admin),
        json={**base, "username": base["username"] + "_3", "role": "driver"},
    )
    assert driver_without_depot.status_code == 422


def test_user_create_rejects_duplicate_username_and_licence(client, db, test_users):
    admin = test_users[0]
    username = f"duplicate_{key().lower()}"
    licence = f"LIC-{key()}"
    payload = {
        "username": username,
        "full_name": "Duplicate Test",
        "password": "ValidPass@123",
        "role": "control_operator",
        "phone": None,
        "driving_license_number": licence,
    }
    first = client.post("/api/v1/users", headers=token_headers(admin), json=payload)
    assert first.status_code == 201, first.text
    duplicate_username = client.post(
        "/api/v1/users", headers=token_headers(admin), json={**payload, "driving_license_number": None}
    )
    assert duplicate_username.status_code == 409
    duplicate_licence = client.post(
        "/api/v1/users",
        headers=token_headers(admin),
        json={**payload, "username": username + "_other"},
    )
    assert duplicate_licence.status_code == 409
    delete_rows(db, db.get(User, first.json()["id"]))


def test_user_list_filters_and_rejects_non_admin(client, test_users):
    admin, driver = test_users
    response = client.get(
        f"/api/v1/users?role=driver&depot_id={driver.depot_id}",
        headers=token_headers(admin),
    )
    assert response.status_code == 200
    assert all(user["role"] == "driver" and user["depot_id"] == driver.depot_id for user in response.json())
    denied = client.get("/api/v1/users", headers=token_headers(driver))
    assert denied.status_code == 403


def test_user_delete_rejects_non_admin(client, db, test_users):
    admin, driver = test_users
    target = add_user(db, "control_operator")
    # The API authorization dependency must reject this before deletion.
    denied = client.delete(f"/api/v1/users/{target.id}", headers=token_headers(driver))
    assert denied.status_code == 403
    assert db.get(User, target.id) is not None
    delete_rows(db, target)


def test_user_delete_conflict_preserves_notice_history(client, db, test_users):
    admin, target = test_users
    suffix = key()
    notice = Notice(
        title=f"Admin test notice {suffix}",
        body="Historical record used by deletion test.",
        audience_json={"roles": ["driver"]},
        publish_at=datetime.now(timezone.utc),
        created_by=target.id,
    )
    db.add(notice)
    db.commit()
    notice_id, target_id = notice.id, target.id

    response = client.delete(f"/api/v1/users/{target_id}", headers=token_headers(admin))
    assert response.status_code == 409
    assert db.get(User, target_id) is not None
    assert db.get(Notice, notice_id) is not None
    delete_rows(db, db.get(Notice, notice_id))


def test_user_delete_conflict_preserves_notice_read_receipt(client, db, test_users):
    admin, target = test_users
    notice = Notice(
        title=f"Receipt test {key()}",
        body="Existing record.",
        audience_json={},
        publish_at=datetime.now(timezone.utc),
        created_by=admin.id,
    )
    db.add(notice)
    db.flush()
    receipt = NoticeRead(notice_id=notice.id, user_id=target.id)
    db.add(receipt)
    db.commit()
    notice_id, target_id = notice.id, target.id

    response = client.delete(f"/api/v1/users/{target_id}", headers=token_headers(admin))
    assert response.status_code == 409
    assert db.get(NoticeRead, (notice_id, target_id)) is not None
    delete_rows(db, db.get(NoticeRead, (notice_id, target_id)), db.get(Notice, notice_id))


def test_cannot_delete_last_depot_manager(client, db, test_users):
    admin = test_users[0]
    depot = add_depot(db)
    manager = add_user(db, "depot_manager", depot_id=depot.id)
    response = client.delete(f"/api/v1/users/{manager.id}", headers=token_headers(admin))
    assert response.status_code == 409
    assert db.get(User, manager.id) is not None
    delete_rows(db, manager, depot)


def test_depot_manager_can_be_deleted_when_another_manager_remains(
    client, db, test_users
):
    admin = test_users[0]
    depot = add_depot(db)
    first = add_user(db, "depot_manager", depot_id=depot.id)
    second = add_user(db, "depot_manager", depot_id=depot.id)

    response = client.delete(f"/api/v1/users/{first.id}", headers=token_headers(admin))
    assert response.status_code == 204
    assert db.get(User, second.id) is not None
    delete_rows(db, second, depot)


def test_user_delete_conflict_preserves_duty_history(client, db, test_users):
    admin, driver = test_users
    depot_id = driver.depot_id
    suffix = key()
    vehicle = Vehicle(reg_no=f"V-{suffix}", depot_id=depot_id, status="active")
    route = Route(code=f"R-{suffix}", name="Duty History Test Route", depot_id=depot_id)
    db.add_all([vehicle, route])
    db.flush()
    duty = Duty(
        service_date=date.today(),
        vehicle_id=vehicle.id,
        driver_id=driver.id,
        route_id=route.id,
        start_time=time(0),
        end_time=time(23, 59),
        status="published",
    )
    db.add(duty)
    db.commit()
    duty_id, driver_id = duty.id, driver.id

    response = client.delete(f"/api/v1/users/{driver_id}", headers=token_headers(admin))
    assert response.status_code == 409
    assert db.get(User, driver_id) is not None
    assert db.get(Duty, duty_id) is not None
    delete_rows(db, db.get(Duty, duty_id), route, vehicle)


def test_admin_and_non_admin_user_create_authorization(client, db, test_users):
    admin, driver = test_users
    payload = {
        "username": f"auth_test_{key().lower()}",
        "full_name": "Authorization Test User",
        "password": "ValidPass@123",
        "role": "control_operator",
    }
    denied = client.post("/api/v1/users", headers=token_headers(driver), json=payload)
    assert denied.status_code == 403
    created = client.post("/api/v1/users", headers=token_headers(admin), json=payload)
    assert created.status_code == 201, created.text
    deleted = client.delete(f"/api/v1/users/{created.json()['id']}", headers=token_headers(admin))
    assert deleted.status_code == 204

