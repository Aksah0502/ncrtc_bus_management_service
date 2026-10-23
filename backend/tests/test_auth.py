
from datetime import timedelta

from app.core.security import create_access_token, hash_password
from app.modules.users.models import User


def test_login_success(client, test_users):
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "test_admin_auto",
            "password": "TestPass@123",
        },
    )

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["access_token"]


def test_login_wrong_password(client, test_users):
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "test_admin_auto",
            "password": "WrongPassword",
        },
    )

    assert response.status_code == 401


def test_me_without_token(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_me_with_valid_token(client, test_users):
    user = test_users[0]
    token = create_access_token(str(user.id))

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["username"] == "test_admin_auto"


def test_me_with_invalid_token(client):
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid.token.value"},
    )

    assert response.status_code == 401


def test_me_with_expired_token(client):
    token = create_access_token(
        "1", expires_delta=timedelta(seconds=-1)
    )

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401



def test_login_with_malformed_password_hash(client, test_users, db):
    user = test_users[0]
    user.password_hash = "not-a-valid-bcrypt-hash"
    db.commit()

    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": user.username,
            "password": "TestPass@123",
        },
    )

    assert response.status_code == 401


def test_me_with_token_for_nonexistent_user(client, db):
    highest_id = db.query(User.id).order_by(User.id.desc()).first()
    nonexistent_id = (highest_id[0] if highest_id else 0) + 1000000

    token = create_access_token(str(nonexistent_id))
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
