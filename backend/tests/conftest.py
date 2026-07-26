import itertools

import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions import db as _db
from app.models import Role, User

_email_counter = itertools.count()


@pytest.fixture()
def app():
    application = create_app("testing")
    yield application


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def db(app):
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def auth_headers(client, db):
    """Factory fixture: auth_headers(role_name, employee_id=None) -> auth header dict.

    Creates a real User row (get-or-create Role), logs in through the real
    /api/auth/login endpoint, and returns {"Authorization": "Bearer ..."}
    ready to pass as `headers=` on any test client call. `employee_id` links
    the account to an Employee so ownership/manager-chain checks resolve.
    """

    def _make(role_name: str, employee_id: int | None = None, password: str = "password123!"):
        email = f"{role_name}-{next(_email_counter)}@example.com"

        role = db.session.query(Role).filter(Role.name == role_name).first()
        if role is None:
            role = Role(name=role_name)
            db.session.add(role)
            db.session.flush()

        user = User(
            email=email,
            password_hash=generate_password_hash(password),
            role=role,
            employee_id=employee_id,
            is_active=True,
        )
        db.session.add(user)
        db.session.commit()

        resp = client.post("/api/auth/login", json={"email": email, "password": password})
        assert resp.status_code == 200, resp.get_json()
        token = resp.get_json()["data"]["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return _make
