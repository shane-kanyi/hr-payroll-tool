def _employee_payload(**overrides):
    payload = {
        "name": "Jane Doe",
        "role": "Engineer",
        "start_date": "2020-01-01",
        "salary": "6000.00",
        "employment_type": "full_time",
    }
    payload.update(overrides)
    return payload


def _create_employee(client, admin_headers, **overrides):
    resp = client.post("/api/employees", json=_employee_payload(**overrides), headers=admin_headers)
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()["data"]


def _generate(client, admin_headers, year=2026, month=7, **overrides):
    payload = {"year": year, "month": month}
    payload.update(overrides)
    return client.post("/api/payroll/generate", json=payload, headers=admin_headers)


def test_generate_payroll_creates_period_and_entries(client, db, auth_headers):
    admin = auth_headers("admin")
    _create_employee(client, admin)

    resp = _generate(client, admin)
    assert resp.status_code == 201
    body = resp.get_json()["data"]
    assert body["year"] == 2026
    assert body["month"] == 7
    assert body["status"] == "draft"
    assert body["entry_count"] == 1


def test_generate_payroll_requires_admin(client, db, auth_headers):
    for role in ("manager", "employee"):
        resp = _generate(client, auth_headers(role))
        assert resp.status_code == 403


def test_generate_payroll_missing_month_returns_400(client, db, auth_headers):
    admin = auth_headers("admin")
    resp = client.post("/api/payroll/generate", json={"year": 2026}, headers=admin)
    assert resp.status_code == 400


def test_generate_payroll_invalid_month_returns_400(client, db, auth_headers):
    admin = auth_headers("admin")
    resp = _generate(client, admin, month=13)
    assert resp.status_code == 400


def test_list_periods(client, db, auth_headers):
    admin = auth_headers("admin")
    _create_employee(client, admin)
    _generate(client, admin, year=2026, month=6)
    _generate(client, admin, year=2026, month=7)

    resp = client.get("/api/payroll/periods", headers=admin)
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["meta"]["total"] == 2


def test_list_periods_requires_admin(client, db, auth_headers):
    resp = client.get("/api/payroll/periods", headers=auth_headers("manager"))
    assert resp.status_code == 403


def test_get_period_by_id(client, db, auth_headers):
    admin = auth_headers("admin")
    _create_employee(client, admin)
    created = _generate(client, admin).get_json()["data"]

    resp = client.get(f"/api/payroll/periods/{created['id']}", headers=admin)
    assert resp.status_code == 200
    assert resp.get_json()["data"]["id"] == created["id"]


def test_get_unknown_period_returns_404(client, db, auth_headers):
    admin = auth_headers("admin")
    resp = client.get("/api/payroll/periods/999", headers=admin)
    assert resp.status_code == 404


def test_list_entries_for_period(client, db, auth_headers):
    admin = auth_headers("admin")
    employee = _create_employee(client, admin)
    period = _generate(client, admin).get_json()["data"]

    resp = client.get(f"/api/payroll/periods/{period['id']}/entries", headers=admin)
    assert resp.status_code == 200
    body = resp.get_json()["data"]
    assert len(body) == 1
    assert body[0]["employee"]["id"] == employee["id"]
    assert body[0]["net_salary"] == "4840.00"


def test_list_entries_for_period_requires_admin(client, db, auth_headers):
    admin = auth_headers("admin")
    _create_employee(client, admin)
    period = _generate(client, admin).get_json()["data"]

    resp = client.get(
        f"/api/payroll/periods/{period['id']}/entries", headers=auth_headers("manager")
    )
    assert resp.status_code == 403


def test_get_own_payslip(client, db, auth_headers):
    admin = auth_headers("admin")
    employee = _create_employee(client, admin)
    employee_headers = auth_headers("employee", employee_id=employee["id"])
    period = _generate(client, admin).get_json()["data"]

    resp = client.get(
        f"/api/payroll/periods/{period['id']}/entries/{employee['id']}", headers=employee_headers
    )
    assert resp.status_code == 200
    assert resp.get_json()["data"]["net_salary"] == "4840.00"


def test_get_someone_elses_payslip_forbidden(client, db, auth_headers):
    admin = auth_headers("admin")
    employee = _create_employee(client, admin, name="Employee")
    other = _create_employee(client, admin, name="Other")
    other_headers = auth_headers("employee", employee_id=other["id"])
    period = _generate(client, admin).get_json()["data"]

    resp = client.get(
        f"/api/payroll/periods/{period['id']}/entries/{employee['id']}", headers=other_headers
    )
    assert resp.status_code == 403


def test_manager_cannot_view_a_reports_payslip(client, db, auth_headers):
    """Payroll is sensitive enough that even a Manager only sees their own -
    per docs/AUTH.md, only Admin can view someone else's payslip."""
    admin = auth_headers("admin")
    manager = _create_employee(client, admin, name="Manager")
    employee = _create_employee(client, admin, name="Report", manager_id=manager["id"])
    manager_headers = auth_headers("manager", employee_id=manager["id"])
    period = _generate(client, admin).get_json()["data"]

    resp = client.get(
        f"/api/payroll/periods/{period['id']}/entries/{employee['id']}", headers=manager_headers
    )
    assert resp.status_code == 403


def test_get_payslip_for_unknown_employee_returns_404(client, db, auth_headers):
    admin = auth_headers("admin")
    _create_employee(client, admin)
    period = _generate(client, admin).get_json()["data"]

    resp = client.get(f"/api/payroll/periods/{period['id']}/entries/999", headers=admin)
    assert resp.status_code == 404


def test_finalize_period(client, db, auth_headers):
    admin = auth_headers("admin")
    _create_employee(client, admin)
    period = _generate(client, admin).get_json()["data"]

    resp = client.post(f"/api/payroll/periods/{period['id']}/finalize", headers=admin)
    assert resp.status_code == 200
    assert resp.get_json()["data"]["status"] == "finalized"


def test_finalize_period_requires_admin(client, db, auth_headers):
    admin = auth_headers("admin")
    _create_employee(client, admin)
    period = _generate(client, admin).get_json()["data"]

    resp = client.post(
        f"/api/payroll/periods/{period['id']}/finalize", headers=auth_headers("manager")
    )
    assert resp.status_code == 403


def test_regenerate_finalized_period_returns_409(client, db, auth_headers):
    admin = auth_headers("admin")
    _create_employee(client, admin)
    period = _generate(client, admin).get_json()["data"]
    client.post(f"/api/payroll/periods/{period['id']}/finalize", headers=admin)

    resp = _generate(client, admin)
    assert resp.status_code == 409


def test_finalize_period_with_no_entries_returns_400(client, db, auth_headers):
    admin = auth_headers("admin")
    period = _generate(client, admin).get_json()["data"]  # no employees created

    resp = client.post(f"/api/payroll/periods/{period['id']}/finalize", headers=admin)
    assert resp.status_code == 400


def test_list_entries_for_employee_across_periods(client, db, auth_headers):
    admin = auth_headers("admin")
    employee = _create_employee(client, admin)
    employee_headers = auth_headers("employee", employee_id=employee["id"])
    _generate(client, admin, year=2026, month=6)
    _generate(client, admin, year=2026, month=7)

    resp = client.get(f"/api/payroll/employees/{employee['id']}/entries", headers=employee_headers)
    assert resp.status_code == 200
    assert len(resp.get_json()["data"]) == 2


def test_list_entries_for_employee_denied_to_others(client, db, auth_headers):
    admin = auth_headers("admin")
    employee = _create_employee(client, admin, name="Employee")
    other = _create_employee(client, admin, name="Other")
    other_headers = auth_headers("employee", employee_id=other["id"])
    _generate(client, admin)

    resp = client.get(f"/api/payroll/employees/{employee['id']}/entries", headers=other_headers)
    assert resp.status_code == 403


def test_payroll_endpoints_require_authentication(client, db):
    assert client.post("/api/payroll/generate", json={"year": 2026, "month": 7}).status_code == 401
    assert client.get("/api/payroll/periods").status_code == 401
