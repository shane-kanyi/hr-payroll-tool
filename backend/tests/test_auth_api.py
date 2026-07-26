def _create_user_via_service(db, email="admin@example.com", role="admin", password="password123!"):
    from app.services.auth_service import AuthService

    return AuthService().create_user({"email": email, "password": password, "role": role})


def test_login_success(client, db):
    _create_user_via_service(db, email="a@example.com", role="admin", password="password123!")

    resp = client.post("/api/auth/login", json={"email": "a@example.com", "password": "password123!"})
    assert resp.status_code == 200
    body = resp.get_json()["data"]
    assert "access_token" in body
    assert body["user"]["email"] == "a@example.com"
    assert body["user"]["role"] == "admin"


def test_login_wrong_password_returns_401(client, db):
    _create_user_via_service(db, email="b@example.com")

    resp = client.post("/api/auth/login", json={"email": "b@example.com", "password": "wrong"})
    assert resp.status_code == 401


def test_login_unknown_email_returns_401(client, db):
    resp = client.post("/api/auth/login", json={"email": "nobody@example.com", "password": "x"})
    assert resp.status_code == 401


def test_login_missing_fields_returns_400(client, db):
    resp = client.post("/api/auth/login", json={"email": "a@example.com"})
    assert resp.status_code == 400


def test_me_requires_authentication(client, db):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_me_returns_current_user(client, db, auth_headers):
    headers = auth_headers("employee")
    resp = client.get("/api/auth/me", headers=headers)
    assert resp.status_code == 200
    assert resp.get_json()["data"]["role"] == "employee"


def test_me_rejects_garbage_token(client, db):
    resp = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert resp.status_code == 401


def test_create_user_requires_admin(client, db, auth_headers):
    headers = auth_headers("employee")
    resp = client.post(
        "/api/auth/users",
        json={"email": "new@example.com", "password": "password123!", "role": "employee"},
        headers=headers,
    )
    assert resp.status_code == 403


def test_admin_can_create_user(client, db, auth_headers):
    headers = auth_headers("admin")
    resp = client.post(
        "/api/auth/users",
        json={"email": "new@example.com", "password": "password123!", "role": "manager"},
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.get_json()["data"]["role"] == "manager"


def test_admin_can_list_users(client, db, auth_headers):
    headers = auth_headers("admin")
    resp = client.get("/api/auth/users", headers=headers)
    assert resp.status_code == 200
    assert len(resp.get_json()["data"]) >= 1  # at least the admin created for this test


def test_non_admin_cannot_list_users(client, db, auth_headers):
    headers = auth_headers("manager")
    resp = client.get("/api/auth/users", headers=headers)
    assert resp.status_code == 403


def test_admin_can_deactivate_and_reactivate_user(client, db, auth_headers):
    admin_headers = auth_headers("admin")
    created = client.post(
        "/api/auth/users",
        json={"email": "toggle@example.com", "password": "password123!", "role": "employee"},
        headers=admin_headers,
    ).get_json()["data"]

    resp = client.post(f"/api/auth/users/{created['id']}/deactivate", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.get_json()["data"]["is_active"] is False

    resp = client.post(f"/api/auth/users/{created['id']}/reactivate", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.get_json()["data"]["is_active"] is True


def test_deactivated_user_token_is_rejected_on_next_request(client, db, auth_headers):
    """The user_lookup_loader re-fetches from the DB every request, so
    deactivating an account mid-session revokes access immediately - the
    old token doesn't keep working until it naturally expires."""
    admin_headers = auth_headers("admin")
    created = client.post(
        "/api/auth/users",
        json={"email": "session@example.com", "password": "password123!", "role": "employee"},
        headers=admin_headers,
    ).get_json()["data"]

    login_resp = client.post(
        "/api/auth/login", json={"email": "session@example.com", "password": "password123!"}
    )
    victim_headers = {"Authorization": f"Bearer {login_resp.get_json()['data']['access_token']}"}

    assert client.get("/api/auth/me", headers=victim_headers).status_code == 200

    client.post(f"/api/auth/users/{created['id']}/deactivate", headers=admin_headers)

    resp = client.get("/api/auth/me", headers=victim_headers)
    assert resp.status_code == 403
