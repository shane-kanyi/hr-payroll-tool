from datetime import date


def _create_team(client, name="Platform"):
    resp = client.post("/api/teams", json={"name": name})
    assert resp.status_code == 201
    return resp.get_json()["data"]


def _employee_payload(**overrides):
    payload = {
        "name": "Jane Doe",
        "role": "Engineer",
        "start_date": "2025-01-01",
        "salary": "5000.00",
        "employment_type": "full_time",
    }
    payload.update(overrides)
    return payload


def _create_employee(client, **overrides):
    resp = client.post("/api/employees", json=_employee_payload(**overrides))
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()["data"]


# ---- teams ----------------------------------------------------------


def test_create_and_list_teams(client, db):
    team = _create_team(client, name="Platform")
    assert team["name"] == "Platform"

    resp = client.get("/api/teams")
    assert resp.status_code == 200
    names = [t["name"] for t in resp.get_json()["data"]]
    assert "Platform" in names


def test_create_duplicate_team_returns_409(client, db):
    _create_team(client, name="Platform")
    resp = client.post("/api/teams", json={"name": "Platform"})
    assert resp.status_code == 409


def test_create_team_missing_name_returns_400(client, db):
    resp = client.post("/api/teams", json={})
    assert resp.status_code == 400
    assert "errors" in resp.get_json()


def test_get_unknown_team_returns_404(client, db):
    resp = client.get("/api/teams/999")
    assert resp.status_code == 404


# ---- employees: create / read ----------------------------------------


def test_create_employee_success(client, db):
    employee = _create_employee(client, name="Jane Doe")
    assert employee["name"] == "Jane Doe"
    assert employee["is_active"] is True
    assert employee["employment_type"] == "full_time"
    assert employee["salary"] == "5000.00"


def test_create_employee_missing_required_field_returns_400(client, db):
    payload = _employee_payload()
    del payload["name"]
    resp = client.post("/api/employees", json=payload)
    assert resp.status_code == 400


def test_create_employee_invalid_employment_type_returns_400(client, db):
    resp = client.post("/api/employees", json=_employee_payload(employment_type="freelance"))
    assert resp.status_code == 400


def test_create_employee_negative_salary_returns_400(client, db):
    resp = client.post("/api/employees", json=_employee_payload(salary="-500"))
    assert resp.status_code == 400


def test_create_employee_with_unknown_team_returns_400(client, db):
    resp = client.post("/api/employees", json=_employee_payload(team_id=999))
    assert resp.status_code == 400


def test_get_employee_by_id(client, db):
    created = _create_employee(client)
    resp = client.get(f"/api/employees/{created['id']}")
    assert resp.status_code == 200
    assert resp.get_json()["data"]["id"] == created["id"]


def test_get_unknown_employee_returns_404(client, db):
    resp = client.get("/api/employees/999")
    assert resp.status_code == 404


# ---- employees: update / lifecycle -----------------------------------


def test_update_employee_partial(client, db):
    created = _create_employee(client, name="Jane Doe")
    resp = client.put(f"/api/employees/{created['id']}", json={"role": "Senior Engineer"})
    assert resp.status_code == 200
    body = resp.get_json()["data"]
    assert body["role"] == "Senior Engineer"
    assert body["name"] == "Jane Doe"  # untouched fields preserved


def test_update_employee_cannot_set_is_active_directly(client, db):
    """is_active is not a field on the update schema. Marshmallow's default
    unknown=RAISE means this is rejected outright with 400, not silently
    ignored - the API refuses the whole request rather than accepting it
    and quietly dropping the one field it doesn't recognize."""
    created = _create_employee(client)
    resp = client.put(f"/api/employees/{created['id']}", json={"is_active": False})
    assert resp.status_code == 400

    # Confirm nothing changed.
    refreshed = client.get(f"/api/employees/{created['id']}").get_json()["data"]
    assert refreshed["is_active"] is True


def test_deactivate_then_reactivate_employee(client, db):
    created = _create_employee(client)

    resp = client.post(f"/api/employees/{created['id']}/deactivate")
    assert resp.status_code == 200
    assert resp.get_json()["data"]["is_active"] is False

    resp = client.post(f"/api/employees/{created['id']}/reactivate")
    assert resp.status_code == 200
    assert resp.get_json()["data"]["is_active"] is True


def test_deactivate_manager_with_active_reports_returns_409(client, db):
    manager = _create_employee(client, name="Manager")
    _create_employee(client, name="Report", manager_id=manager["id"])

    resp = client.post(f"/api/employees/{manager['id']}/deactivate")
    assert resp.status_code == 409
    assert "blocking_reports" in resp.get_json()


def test_update_employee_circular_manager_returns_400(client, db):
    a = _create_employee(client, name="A")
    b = _create_employee(client, name="B", manager_id=a["id"])

    resp = client.put(f"/api/employees/{a['id']}", json={"manager_id": b["id"]})
    assert resp.status_code == 400


# ---- employees: list / filters / org chart ----------------------------


def test_list_employees_default_pagination_meta(client, db):
    _create_employee(client, name="Alice")
    _create_employee(client, name="Bob")

    resp = client.get("/api/employees")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["meta"]["total"] == 2
    assert body["meta"]["page"] == 1
    assert body["meta"]["per_page"] == 20


def test_list_employees_search_filter(client, db):
    _create_employee(client, name="Alice Anderson")
    _create_employee(client, name="Bob Brown")

    resp = client.get("/api/employees?search=ali")
    body = resp.get_json()
    assert body["meta"]["total"] == 1
    assert body["data"][0]["name"] == "Alice Anderson"


def test_org_chart_endpoint(client, db):
    ceo = _create_employee(client, name="CEO")
    _create_employee(client, name="VP", manager_id=ceo["id"])

    resp = client.get("/api/employees/org-chart")
    assert resp.status_code == 200
    data = resp.get_json()["data"]
    assert len(data) == 1
    assert data[0]["name"] == "CEO"
    assert data[0]["children"][0]["name"] == "VP"
