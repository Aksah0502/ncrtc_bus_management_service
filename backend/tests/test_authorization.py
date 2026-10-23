
import pytest
from fastapi import HTTPException

from app.api.dependencies import require_roles
from app.core.authorization import ensure_depot_access


def test_admin_role_allowed(test_users):
    admin = test_users[0]
    check_admin = require_roles("admin")

    assert check_admin(current_user=admin) == admin


def test_driver_rejected_from_admin_only_action(test_users):
    driver = test_users[1]
    check_admin = require_roles("admin")

    with pytest.raises(HTTPException) as exc:
        check_admin(current_user=driver)

    assert exc.value.status_code == 403


def test_user_can_access_own_depot(test_users):
    driver = test_users[1]

    ensure_depot_access(driver, driver.depot_id)


def test_user_cannot_access_another_depot(test_users):
    driver = test_users[1]
    other_depot_id = (driver.depot_id or 0) + 1000

    with pytest.raises(HTTPException) as exc:
        ensure_depot_access(driver, other_depot_id)

    assert exc.value.status_code == 403


from app.core.authorization import resolve_depot_filter


def test_depot_scoped_user_without_depot_is_rejected(test_users):
    driver = test_users[1]
    driver.depot_id = None

    with pytest.raises(HTTPException) as exc:
        resolve_depot_filter(driver)

    assert exc.value.status_code == 403


def test_driver_filter_is_limited_to_own_depot(test_users):
    driver = test_users[1]

    result = resolve_depot_filter(driver)

    assert result == driver.depot_id


def test_driver_cannot_request_another_depot(test_users):
    driver = test_users[1]
    other_depot_id = driver.depot_id + 1000

    with pytest.raises(HTTPException) as exc:
        resolve_depot_filter(driver, other_depot_id)

    assert exc.value.status_code == 403


def test_admin_can_request_specific_depot(test_users):
    admin = test_users[0]
    requested_depot_id = 999

    result = resolve_depot_filter(admin, requested_depot_id)

    assert result == requested_depot_id
