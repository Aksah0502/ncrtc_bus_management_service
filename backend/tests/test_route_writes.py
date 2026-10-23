
import pytest

from app.core.security import create_access_token
from app.modules.routes.models import Route, Stop
from app.modules.routes.models import Route, RouteStop, Stop

def auth(user):
    token = create_access_token(str(user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def route_stops(db):
    stops = [
        Stop(name="Test Route Stop A", lat=28.60, lng=77.20),
        Stop(name="Test Route Stop B", lat=28.61, lng=77.21),
    ]
    db.add_all(stops)
    db.commit()

    for stop in stops:
        db.refresh(stop)

    yield stops

    db.delete(stops[0])
    db.delete(stops[1])
    db.commit()


def test_admin_can_create_route(client, test_users, route_stops):
    admin = test_users[0]
    depot_id = admin.depot_id
    assert depot_id is not None

    response = client.post(
        "/api/v1/routes",
        headers=auth(admin),
        json={
            "code": "TEST-ROUTE-01",
            "name": "Test Route",
            "depot_id": depot_id,
            "route_stops": [
                {
                    "sequence": 1,
                    "stop_id": route_stops[0].id,
                    "planned_offset_min": 0,
                },
                {
                    "sequence": 2,
                    "stop_id": route_stops[1].id,
                    "planned_offset_min": 15,
                },
            ],
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["code"] == "TEST-ROUTE-01"
    assert [item["sequence"] for item in body["route_stops"]] == [1, 2]

    created = client.delete(
        f"/api/v1/routes/{body['id']}",
        headers=auth(admin),
    )
    assert created.status_code == 204


def test_driver_cannot_create_route(client, test_users, route_stops):
    driver = test_users[1]

    response = client.post(
        "/api/v1/routes",
        headers=auth(driver),
        json={
            "code": "TEST-ROUTE-02",
            "name": "Forbidden Route",
            "depot_id": driver.depot_id,
            "route_stops": [
                {
                    "sequence": 1,
                    "stop_id": route_stops[0].id,
                    "planned_offset_min": 0,
                }
            ],
        },
    )

    assert response.status_code == 403


def test_create_route_rejects_duplicate_sequences(
    client, test_users, route_stops
):
    admin = test_users[0]

    response = client.post(
        "/api/v1/routes",
        headers=auth(admin),
        json={
            "code": "TEST-ROUTE-03",
            "name": "Invalid Route",
            "depot_id": admin.depot_id,
            "route_stops": [
                {
                    "sequence": 1,
                    "stop_id": route_stops[0].id,
                    "planned_offset_min": 0,
                },
                {
                    "sequence": 1,
                    "stop_id": route_stops[1].id,
                    "planned_offset_min": 10,
                },
            ],
        },
    )

    assert response.status_code == 422


def test_admin_can_update_route(
    client, test_users, route_stops, db
):
    admin = test_users[0]
    assert admin.depot_id is not None

    route = Route(
        code="TEST-ROUTE-04",
        name="Before Update",
        depot_id=admin.depot_id,
    )
    route.route_stops.append(
        RouteStop(
            sequence=1,
            stop_id=route_stops[0].id,
            planned_offset_min=0,
        )
    )
    db.add(route)
    db.commit()
    db.refresh(route)
    route_id = route.id

    response = client.patch(
        f"/api/v1/routes/{route_id}",
        headers=auth(admin),
        json={"name": "After Update"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["name"] == "After Update"

    db.delete(route)
    db.commit()


def test_delete_missing_route_returns_404(client, test_users):
    response = client.delete(
        "/api/v1/routes/999999999",
        headers=auth(test_users[0]),
    )
    assert response.status_code == 404
