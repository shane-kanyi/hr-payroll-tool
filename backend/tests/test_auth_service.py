from datetime import date

import pytest

from app.services.auth_service import AuthService
from app.services.employee_service import EmployeeService
from app.utils.errors import ConflictError, NotFoundError, UnauthorizedError, ValidationError


def _employee_data(**overrides):
    data = {
        "name": "Jane Doe",
        "role": "Engineer",
        "start_date": date(2020, 1, 1),
        "salary": "5000.00",
        "employment_type": "full_time",
    }
    data.update(overrides)
    return data


@pytest.fixture()
def auth_service():
    return AuthService()


@pytest.fixture()
def emp_service():
    return EmployeeService()


def _user_data(**overrides):
    data = {"email": "user@example.com", "password": "supersecret1", "role": "employee"}
    data.update(overrides)
    return data


def test_create_user_and_authenticate_succeeds(db, auth_service):
    auth_service.create_user(_user_data(email="admin@example.com", role="admin"))

    user = auth_service.authenticate("admin@example.com", "supersecret1")
    assert user.email == "admin@example.com"
    assert user.role.name == "admin"


def test_authenticate_wrong_password_raises_unauthorized(db, auth_service):
    auth_service.create_user(_user_data(email="a@example.com"))

    with pytest.raises(UnauthorizedError):
        auth_service.authenticate("a@example.com", "wrong-password")


def test_authenticate_unknown_email_raises_unauthorized(db, auth_service):
    with pytest.raises(UnauthorizedError):
        auth_service.authenticate("nobody@example.com", "whatever")


def test_authenticate_deactivated_account_raises_unauthorized(db, auth_service):
    user = auth_service.create_user(_user_data(email="b@example.com"))
    auth_service.deactivate_user(user.id)

    with pytest.raises(UnauthorizedError):
        auth_service.authenticate("b@example.com", "supersecret1")


def test_create_user_rejects_duplicate_email(db, auth_service):
    auth_service.create_user(_user_data(email="dup@example.com"))

    with pytest.raises(ConflictError):
        auth_service.create_user(_user_data(email="dup@example.com"))


def test_create_user_rejects_unknown_role(db, auth_service):
    with pytest.raises(ValidationError):
        auth_service.create_user(_user_data(role="superuser"))


def test_create_user_links_to_employee(db, auth_service, emp_service):
    employee = emp_service.create_employee(_employee_data())
    user = auth_service.create_user(_user_data(employee_id=employee.id))
    assert user.employee_id == employee.id


def test_create_user_rejects_unknown_employee(db, auth_service):
    with pytest.raises(ValidationError):
        auth_service.create_user(_user_data(employee_id=999))


def test_create_user_rejects_employee_already_linked(db, auth_service, emp_service):
    employee = emp_service.create_employee(_employee_data())
    auth_service.create_user(_user_data(email="first@example.com", employee_id=employee.id))

    with pytest.raises(ConflictError):
        auth_service.create_user(_user_data(email="second@example.com", employee_id=employee.id))


def test_deactivate_already_inactive_user_raises_conflict(db, auth_service):
    user = auth_service.create_user(_user_data())
    auth_service.deactivate_user(user.id)

    with pytest.raises(ConflictError):
        auth_service.deactivate_user(user.id)


def test_reactivate_user(db, auth_service):
    user = auth_service.create_user(_user_data())
    auth_service.deactivate_user(user.id)

    reactivated = auth_service.reactivate_user(user.id)
    assert reactivated.is_active is True


def test_get_user_raises_not_found(db, auth_service):
    with pytest.raises(NotFoundError):
        auth_service.get_user(999)


def test_password_is_hashed_not_stored_plaintext(db, auth_service):
    user = auth_service.create_user(_user_data(password="supersecret1"))
    assert user.password_hash != "supersecret1"
    assert user.password_hash.count("$") >= 2  # werkzeug's hash format
