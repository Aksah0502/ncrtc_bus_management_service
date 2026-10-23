
from app.modules.fleet.models import Depot, Vehicle
import pytest
from fastapi import status
from app.core.security import create_access_token


def test_depots_requires_authentication(client):
    response = client.get("/api/v1/fleet/depots")
    assert response.status_code == 401


def test_driver_sees_only_assigned_depot(client, test_users):
    driver = test_users[1]

    response = client.get(
        "/api/v1/fleet/depots",
        headers={
            "Authorization": f"Bearer {__import__('app.core.security', fromlist=['create_access_token']).create_access_token(str(driver.id))}"
        },
    )

    assert response.status_code == 200
    assert all(item["id"] == driver.depot_id for item in response.json())


def test_driver_cannot_request_another_depot(client, test_users):
    driver = test_users[1]
    from app.core.security import create_access_token

    token = create_access_token(str(driver.id))
    response = client.get(
        f"/api/v1/fleet/vehicles?depot_id={driver.depot_id + 1000}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_vehicles_requires_authentication(client):
    response = client.get("/api/v1/fleet/vehicles")
    assert response.status_code == 401


def test_admin_can_list_depots(client, test_users):
    from app.core.security import create_access_token

    admin = test_users[0]
    token = create_access_token(str(admin.id))
    response = client.get(
        "/api/v1/fleet/depots",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.fixture
def test_vehicle(db, test_users):
    driver = test_users[1]

    vehicle = Vehicle(
        reg_no="TEST-DETAIL-001",
        depot_id=driver.depot_id,
        status="active",
    )

    existing = db.query(Vehicle).filter_by(
        reg_no="TEST-DETAIL-001"
    ).first()

    if existing:
        db.delete(existing)
        db.commit()

    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)

    yield vehicle

    db.delete(vehicle)
    db.commit()


def test_vehicle_detail_requires_authentication(client, test_vehicle):
    response = client.get(
        f"/api/v1/fleet/vehicles/{test_vehicle.id}"
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_admin_can_get_vehicle_detail(client, test_users, test_vehicle):
    admin = test_users[0]
    token = create_access_token(str(admin.id))

    response = client.get(
        f"/api/v1/fleet/vehicles/{test_vehicle.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == test_vehicle.id
    assert response.json()["reg_no"] == test_vehicle.reg_no


def test_driver_can_get_vehicle_from_own_depot(
    client, test_users, test_vehicle
):
    driver = test_users[1]
    token = create_access_token(str(driver.id))

    response = client.get(
        f"/api/v1/fleet/vehicles/{test_vehicle.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_200_OK


def test_vehicle_detail_returns_404_for_missing_vehicle(
    client, test_users
):
    admin = test_users[0]
    token = create_access_token(str(admin.id))

    response = client.get(
        "/api/v1/fleet/vehicles/999999999",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
