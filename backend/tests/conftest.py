
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings

if settings.postgres_db != "ncrtc_bms_test":
    raise RuntimeError(
        "Tests must run against ncrtc_bms_test. "
        "Set POSTGRES_DB=ncrtc_bms_test before running pytest."
    )

from app.main import app
from app.db.session import SessionLocal, get_db
from app.core.security import hash_password
from app.modules.users.models import User
from app.modules.fleet.models import Depot


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def test_users(db):
    depot = db.query(Depot).filter_by(code="TEST_AUTO").first()

    if depot is None:
        depot = Depot(
            code="TEST_AUTO",
            name="Automated Test Depot",
            location_lat=28.6,
            location_lng=77.2,
        )
        db.add(depot)
        db.commit()
        db.refresh(depot)

    depot_id = depot.id
    usernames = ("test_admin_auto", "test_driver_auto")

    try:
        for username in usernames:
            existing = db.query(User).filter_by(username=username).first()
            if existing:
                db.delete(existing)
        db.commit()

        users = [
            User(
                username="test_admin_auto",
                password_hash=hash_password("TestPass@123"),
                full_name="Test Admin",
                role="admin",
                depot_id=depot_id,
            ),
            User(
                username="test_driver_auto",
                password_hash=hash_password("TestPass@123"),
                full_name="Test Driver",
                role="driver",
                depot_id=depot_id,
            ),
        ]

        db.add_all(users)
        db.commit()
        for user in users:
            db.refresh(user)

        yield users
    finally:
        for username in usernames:
            user = db.query(User).filter_by(username=username).first()
            if user:
                db.delete(user)
        db.commit()


@pytest.fixture
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)
