
from app.core.security import create_access_token


def auth_header(user):
    token = create_access_token(str(user.id))
    return {"Authorization": f"Bearer {token}"}


def test_routes_requires_authentication(client):
    response = client.get("/api/v1/routes")
    assert response.status_code == 401


def test_admin_can_list_routes(client, test_users):
    response = client.get(
        "/api/v1/routes",
        headers=auth_header(test_users[0]),
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_driver_cannot_list_routes(client, test_users):
    driver = test_users[1]
    response = client.get(
        "/api/v1/routes",
        headers=auth_header(driver),
    )
    assert response.status_code == 403


def test_duties_require_authentication(client):
    response = client.get("/api/v1/scheduling/duties")
    assert response.status_code == 401


def test_admin_can_list_duties(client, test_users):
    response = client.get(
        "/api/v1/scheduling/duties",
        headers=auth_header(test_users[0]),
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_driver_sees_only_own_duties(client, test_users):
    driver = test_users[1]
    response = client.get(
        "/api/v1/scheduling/duties",
        headers=auth_header(driver),
    )

    assert response.status_code == 200
    assert all(
        duty["driver_id"] == driver.id
        for duty in response.json()
    )


def test_driver_cannot_request_another_depots_routes(
    client, test_users
):
    driver = test_users[1]
    response = client.get(
        f"/api/v1/routes?depot_id={driver.depot_id + 1000}",
        headers=auth_header(driver),
    )
    assert response.status_code == 403
