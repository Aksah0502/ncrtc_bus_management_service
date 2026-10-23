
from app.core.security import create_access_token


def headers(user):
    return {
        "Authorization": f"Bearer {create_access_token(str(user.id))}"
    }


def test_stops_requires_authentication(client):
    assert client.get("/api/v1/routes/stops").status_code == 401


def test_driver_cannot_list_stops(client, test_users):
    response = client.get(
        "/api/v1/routes/stops",
        headers=headers(test_users[1]),
    )
    assert response.status_code == 403


def test_admin_can_list_stops(client, test_users):
    response = client.get(
        "/api/v1/routes/stops",
        headers=headers(test_users[0]),
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_route_detail_returns_404_for_missing_route(client, test_users):
    response = client.get(
        "/api/v1/routes/999999999",
        headers=headers(test_users[0]),
    )
    assert response.status_code == 404


def test_driver_cannot_view_route_details(client, test_users):
    response = client.get(
        "/api/v1/routes/1",
        headers=headers(test_users[1]),
    )
    assert response.status_code == 403
