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


def _create_employee(client, **overrides):
    resp = client.post("/api/employees", json=_employee_payload(**overrides))
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()["data"]


def _generate(client, year=2026, month=7, **overrides):
    payload = {"year": year, "month": month}
    payload.update(overrides)
    return client.post("/api/payroll/generate", json=payload)


def test_generate_payroll_creates_period_and_entries(client, db):
    employee = _create_employee(client)

    resp = _generate(client)
    assert resp.status_code == 201
    body = resp.get_json()["data"]
    assert body["year"] == 2026
    assert body["month"] == 7
    assert body["status"] == "draft"
    assert body["entry_count"] == 1


def test_generate_payroll_missing_month_returns_400(client, db):
    resp = client.post("/api/payroll/generate", json={"year": 2026})
    assert resp.status_code == 400


def test_generate_payroll_invalid_month_returns_400(client, db):
    resp = _generate(client, month=13)
    assert resp.status_code == 400


def test_list_periods(client, db):
    _create_employee(client)
    _generate(client, year=2026, month=6)
    _generate(client, year=2026, month=7)

    resp = client.get("/api/payroll/periods")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["meta"]["total"] == 2


def test_get_period_by_id(client, db):
    _create_employee(client)
    created = _generate(client).get_json()["data"]

    resp = client.get(f"/api/payroll/periods/{created['id']}")
    assert resp.status_code == 200
    assert resp.get_json()["data"]["id"] == created["id"]


def test_get_unknown_period_returns_404(client, db):
    resp = client.get("/api/payroll/periods/999")
    assert resp.status_code == 404


def test_list_entries_for_period(client, db):
    employee = _create_employee(client)
    period = _generate(client).get_json()["data"]

    resp = client.get(f"/api/payroll/periods/{period['id']}/entries")
    assert resp.status_code == 200
    body = resp.get_json()["data"]
    assert len(body) == 1
    assert body[0]["employee"]["id"] == employee["id"]
    assert body[0]["net_salary"] == "4840.00"


def test_get_single_payslip(client, db):
    employee = _create_employee(client)
    period = _generate(client).get_json()["data"]

    resp = client.get(f"/api/payroll/periods/{period['id']}/entries/{employee['id']}")
    assert resp.status_code == 200
    assert resp.get_json()["data"]["net_salary"] == "4840.00"


def test_get_payslip_for_unknown_employee_returns_404(client, db):
    _create_employee(client)
    period = _generate(client).get_json()["data"]

    resp = client.get(f"/api/payroll/periods/{period['id']}/entries/999")
    assert resp.status_code == 404


def test_finalize_period(client, db):
    _create_employee(client)
    period = _generate(client).get_json()["data"]

    resp = client.post(f"/api/payroll/periods/{period['id']}/finalize")
    assert resp.status_code == 200
    assert resp.get_json()["data"]["status"] == "finalized"


def test_regenerate_finalized_period_returns_409(client, db):
    _create_employee(client)
    period = _generate(client).get_json()["data"]
    client.post(f"/api/payroll/periods/{period['id']}/finalize")

    resp = _generate(client)
    assert resp.status_code == 409


def test_finalize_period_with_no_entries_returns_400(client, db):
    period = _generate(client).get_json()["data"]  # no employees created

    resp = client.post(f"/api/payroll/periods/{period['id']}/finalize")
    assert resp.status_code == 400


def test_list_entries_for_employee_across_periods(client, db):
    employee = _create_employee(client)
    _generate(client, year=2026, month=6)
    _generate(client, year=2026, month=7)

    resp = client.get(f"/api/payroll/employees/{employee['id']}/entries")
    assert resp.status_code == 200
    assert len(resp.get_json()["data"]) == 2
