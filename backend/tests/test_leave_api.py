from datetime import date


def _employee_payload(**overrides):
    payload = {
        "name": "Jane Doe",
        "role": "Engineer",
        "start_date": "2020-01-01",
        "salary": "5000.00",
        "employment_type": "full_time",
    }
    payload.update(overrides)
    return payload


def _create_employee(client, **overrides):
    resp = client.post("/api/employees", json=_employee_payload(**overrides))
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()["data"]


def _submit_leave(client, employee_id, **overrides):
    payload = {
        "employee_id": employee_id,
        "leave_type": "sick",  # exempt from notice period, simplest for API tests
        "start_date": "2026-06-08",
        "end_date": "2026-06-08",
    }
    payload.update(overrides)
    return client.post("/api/leave-requests", json=payload)


# ---- submit -------------------------------------------------------------


def test_submit_leave_request_success(client, db):
    employee = _create_employee(client)
    resp = _submit_leave(client, employee["id"])

    assert resp.status_code == 201
    body = resp.get_json()["data"]
    assert body["status"] == "pending"
    assert body["leave_type"] == "sick"
    assert body["employee"]["id"] == employee["id"]


def test_submit_leave_request_missing_field_returns_400(client, db):
    employee = _create_employee(client)
    payload = {
        "employee_id": employee["id"],
        "leave_type": "sick",
        "start_date": "2026-06-08",
        # end_date missing
    }
    resp = client.post("/api/leave-requests", json=payload)
    assert resp.status_code == 400


def test_submit_leave_request_unknown_employee_returns_404(client, db):
    resp = _submit_leave(client, 999)
    assert resp.status_code == 404


def test_submit_overlapping_leave_returns_409(client, db):
    employee = _create_employee(client)
    _submit_leave(client, employee["id"], start_date="2026-06-08", end_date="2026-06-10")

    resp = _submit_leave(client, employee["id"], start_date="2026-06-09", end_date="2026-06-11")
    assert resp.status_code == 409
    assert "conflicting_request_ids" in resp.get_json()


def test_submit_annual_leave_insufficient_notice_returns_400(client, db):
    employee = _create_employee(client)
    resp = _submit_leave(
        client, employee["id"], leave_type="annual",
        start_date="2026-06-02", end_date="2026-06-02",
    )
    assert resp.status_code == 400


# ---- read / list ----------------------------------------------------------


def test_get_leave_request_by_id(client, db):
    employee = _create_employee(client)
    created = _submit_leave(client, employee["id"]).get_json()["data"]

    resp = client.get(f"/api/leave-requests/{created['id']}")
    assert resp.status_code == 200
    assert resp.get_json()["data"]["id"] == created["id"]


def test_get_unknown_leave_request_returns_404(client, db):
    resp = client.get("/api/leave-requests/999")
    assert resp.status_code == 404


def test_list_leave_requests_filters_by_employee(client, db):
    a = _create_employee(client, name="Alice")
    b = _create_employee(client, name="Bob")
    _submit_leave(client, a["id"])
    _submit_leave(client, b["id"])

    resp = client.get(f"/api/leave-requests?employee_id={a['id']}")
    body = resp.get_json()
    assert body["meta"]["total"] == 1
    assert body["data"][0]["employee"]["id"] == a["id"]


# ---- approve / reject -----------------------------------------------------


def test_approve_leave_request(client, db):
    manager = _create_employee(client, name="Manager")
    employee = _create_employee(client, name="Report", manager_id=manager["id"])
    request = _submit_leave(client, employee["id"]).get_json()["data"]

    resp = client.post(
        f"/api/leave-requests/{request['id']}/approve",
        json={"acting_manager_id": manager["id"], "notes": "ok"},
    )
    assert resp.status_code == 200
    body = resp.get_json()["data"]
    assert body["status"] == "approved"
    assert body["decided_by"]["id"] == manager["id"]


def test_approve_own_request_returns_403(client, db):
    manager = _create_employee(client, name="Manager")
    request = _submit_leave(client, manager["id"]).get_json()["data"]

    resp = client.post(
        f"/api/leave-requests/{request['id']}/approve",
        json={"acting_manager_id": manager["id"]},
    )
    assert resp.status_code == 403


def test_reject_leave_request(client, db):
    manager = _create_employee(client, name="Manager")
    employee = _create_employee(client, name="Report", manager_id=manager["id"])
    request = _submit_leave(client, employee["id"]).get_json()["data"]

    resp = client.post(
        f"/api/leave-requests/{request['id']}/reject",
        json={"acting_manager_id": manager["id"]},
    )
    assert resp.status_code == 200
    assert resp.get_json()["data"]["status"] == "rejected"


def test_approve_already_decided_request_returns_409(client, db):
    manager = _create_employee(client, name="Manager")
    employee = _create_employee(client, name="Report", manager_id=manager["id"])
    request = _submit_leave(client, employee["id"]).get_json()["data"]
    client.post(
        f"/api/leave-requests/{request['id']}/approve",
        json={"acting_manager_id": manager["id"]},
    )

    resp = client.post(
        f"/api/leave-requests/{request['id']}/reject",
        json={"acting_manager_id": manager["id"]},
    )
    assert resp.status_code == 409


# ---- cancel -----------------------------------------------------------


def test_cancel_own_pending_request(client, db):
    employee = _create_employee(client)
    request = _submit_leave(client, employee["id"]).get_json()["data"]

    resp = client.post(
        f"/api/leave-requests/{request['id']}/cancel",
        json={"actor_employee_id": employee["id"]},
    )
    assert resp.status_code == 200
    assert resp.get_json()["data"]["status"] == "cancelled"


def test_cancel_someone_elses_request_returns_403(client, db):
    employee = _create_employee(client, name="Employee")
    other = _create_employee(client, name="Other")
    request = _submit_leave(client, employee["id"]).get_json()["data"]

    resp = client.post(
        f"/api/leave-requests/{request['id']}/cancel",
        json={"actor_employee_id": other["id"]},
    )
    assert resp.status_code == 403


# ---- balances / dashboard-style reads ------------------------------------


def test_get_leave_balances_auto_provisions(client, db):
    employee = _create_employee(client)
    resp = client.get(f"/api/leave-requests/balances?employee_id={employee['id']}&year=2026")
    assert resp.status_code == 200
    types = {b["leave_type"] for b in resp.get_json()["data"]}
    assert types == {"annual", "sick"}


def test_get_leave_balances_missing_employee_id_returns_400(client, db):
    resp = client.get("/api/leave-requests/balances")
    assert resp.status_code == 400


def test_who_is_on_leave(client, db):
    manager = _create_employee(client, name="Manager")
    employee = _create_employee(client, name="Report", manager_id=manager["id"])
    request = _submit_leave(
        client, employee["id"], start_date="2026-06-08", end_date="2026-06-08"
    ).get_json()["data"]
    client.post(
        f"/api/leave-requests/{request['id']}/approve",
        json={"acting_manager_id": manager["id"]},
    )

    resp = client.get("/api/leave-requests/on-leave?date=2026-06-08")
    assert resp.status_code == 200
    ids = [r["employee"]["id"] for r in resp.get_json()["data"]]
    assert employee["id"] in ids


def test_pending_approvals_for_manager(client, db):
    manager = _create_employee(client, name="Manager")
    employee = _create_employee(client, name="Report", manager_id=manager["id"])
    _submit_leave(client, employee["id"])

    resp = client.get(f"/api/leave-requests/pending-approvals?manager_id={manager['id']}")
    assert resp.status_code == 200
    assert len(resp.get_json()["data"]) == 1


def test_pending_approvals_missing_manager_id_returns_400(client, db):
    resp = client.get("/api/leave-requests/pending-approvals")
    assert resp.status_code == 400


def test_escalation_sweep_endpoint(client, db):
    resp = client.post("/api/leave-requests/escalate")
    assert resp.status_code == 200
    assert resp.get_json()["meta"]["escalated_count"] == 0
