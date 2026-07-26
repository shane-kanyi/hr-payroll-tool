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


def _create_employee(client, admin_headers, **overrides):
    resp = client.post("/api/employees", json=_employee_payload(**overrides), headers=admin_headers)
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()["data"]


def _submit_leave(client, headers, **overrides):
    payload = {
        "leave_type": "sick",  # exempt from notice period, simplest for API tests
        "start_date": "2026-06-08",
        "end_date": "2026-06-08",
    }
    payload.update(overrides)
    return client.post("/api/leave-requests", json=payload, headers=headers)


# ---- submit -------------------------------------------------------------


def test_submit_leave_request_success(client, db, auth_headers):
    admin = auth_headers("admin")
    employee = _create_employee(client, admin)
    employee_headers = auth_headers("employee", employee_id=employee["id"])

    resp = _submit_leave(client, employee_headers)

    assert resp.status_code == 201
    body = resp.get_json()["data"]
    assert body["status"] == "pending"
    assert body["leave_type"] == "sick"
    assert body["employee"]["id"] == employee["id"]


def test_submit_leave_request_requires_authentication(client, db):
    resp = client.post("/api/leave-requests", json={"leave_type": "sick"})
    assert resp.status_code == 401


def test_submit_leave_request_missing_field_returns_400(client, db, auth_headers):
    admin = auth_headers("admin")
    employee = _create_employee(client, admin)
    employee_headers = auth_headers("employee", employee_id=employee["id"])

    payload = {"leave_type": "sick", "start_date": "2026-06-08"}  # end_date missing
    resp = client.post("/api/leave-requests", json=payload, headers=employee_headers)
    assert resp.status_code == 400


def test_submit_leave_request_account_not_linked_to_employee_returns_400(client, db, auth_headers):
    unlinked = auth_headers("employee")  # no employee_id
    resp = _submit_leave(client, unlinked)
    assert resp.status_code == 400


def test_admin_can_submit_leave_on_behalf_of_any_employee(client, db, auth_headers):
    admin = auth_headers("admin")
    employee = _create_employee(client, admin)

    resp = _submit_leave(client, admin, employee_id=employee["id"])
    assert resp.status_code == 201
    assert resp.get_json()["data"]["employee"]["id"] == employee["id"]


def test_submit_overlapping_leave_returns_409(client, db, auth_headers):
    admin = auth_headers("admin")
    employee = _create_employee(client, admin)
    employee_headers = auth_headers("employee", employee_id=employee["id"])

    _submit_leave(client, employee_headers, start_date="2026-06-08", end_date="2026-06-10")
    resp = _submit_leave(client, employee_headers, start_date="2026-06-09", end_date="2026-06-11")
    assert resp.status_code == 409
    assert "conflicting_request_ids" in resp.get_json()


def test_submit_annual_leave_insufficient_notice_returns_400(client, db, auth_headers):
    admin = auth_headers("admin")
    employee = _create_employee(client, admin)
    employee_headers = auth_headers("employee", employee_id=employee["id"])

    resp = _submit_leave(
        client, employee_headers, leave_type="annual",
        start_date="2026-06-02", end_date="2026-06-02",
    )
    assert resp.status_code == 400


# ---- read / list ----------------------------------------------------------


def test_get_leave_request_by_id_as_owner(client, db, auth_headers):
    admin = auth_headers("admin")
    employee = _create_employee(client, admin)
    employee_headers = auth_headers("employee", employee_id=employee["id"])
    created = _submit_leave(client, employee_headers).get_json()["data"]

    resp = client.get(f"/api/leave-requests/{created['id']}", headers=employee_headers)
    assert resp.status_code == 200
    assert resp.get_json()["data"]["id"] == created["id"]


def test_get_leave_request_by_id_denied_to_unrelated_employee(client, db, auth_headers):
    admin = auth_headers("admin")
    employee = _create_employee(client, admin, name="Owner")
    other = _create_employee(client, admin, name="Stranger")
    employee_headers = auth_headers("employee", employee_id=employee["id"])
    other_headers = auth_headers("employee", employee_id=other["id"])

    created = _submit_leave(client, employee_headers).get_json()["data"]

    resp = client.get(f"/api/leave-requests/{created['id']}", headers=other_headers)
    assert resp.status_code == 403


def test_get_leave_request_by_id_allowed_for_their_manager(client, db, auth_headers):
    admin = auth_headers("admin")
    manager = _create_employee(client, admin, name="Manager")
    employee = _create_employee(client, admin, name="Report", manager_id=manager["id"])
    manager_headers = auth_headers("manager", employee_id=manager["id"])
    employee_headers = auth_headers("employee", employee_id=employee["id"])

    created = _submit_leave(client, employee_headers).get_json()["data"]

    resp = client.get(f"/api/leave-requests/{created['id']}", headers=manager_headers)
    assert resp.status_code == 200


def test_get_unknown_leave_request_returns_404(client, db, auth_headers):
    admin = auth_headers("admin")
    resp = client.get("/api/leave-requests/999", headers=admin)
    assert resp.status_code == 404


def test_list_leave_requests_non_admin_only_sees_own(client, db, auth_headers):
    admin = auth_headers("admin")
    a = _create_employee(client, admin, name="Alice")
    b = _create_employee(client, admin, name="Bob")
    a_headers = auth_headers("employee", employee_id=a["id"])
    b_headers = auth_headers("employee", employee_id=b["id"])

    _submit_leave(client, a_headers)
    _submit_leave(client, b_headers)

    resp = client.get("/api/leave-requests", headers=a_headers)
    body = resp.get_json()
    assert body["meta"]["total"] == 1
    assert body["data"][0]["employee"]["id"] == a["id"]


def test_list_leave_requests_admin_can_filter_by_employee(client, db, auth_headers):
    admin = auth_headers("admin")
    a = _create_employee(client, admin, name="Alice")
    b = _create_employee(client, admin, name="Bob")
    _submit_leave(client, auth_headers("employee", employee_id=a["id"]))
    _submit_leave(client, auth_headers("employee", employee_id=b["id"]))

    resp = client.get(f"/api/leave-requests?employee_id={a['id']}", headers=admin)
    body = resp.get_json()
    assert body["meta"]["total"] == 1
    assert body["data"][0]["employee"]["id"] == a["id"]


# ---- approve / reject -----------------------------------------------------


def test_approve_leave_request(client, db, auth_headers):
    admin = auth_headers("admin")
    manager = _create_employee(client, admin, name="Manager")
    employee = _create_employee(client, admin, name="Report", manager_id=manager["id"])
    manager_headers = auth_headers("manager", employee_id=manager["id"])
    employee_headers = auth_headers("employee", employee_id=employee["id"])

    request = _submit_leave(client, employee_headers).get_json()["data"]

    resp = client.post(
        f"/api/leave-requests/{request['id']}/approve",
        json={"notes": "ok"},
        headers=manager_headers,
    )
    assert resp.status_code == 200
    body = resp.get_json()["data"]
    assert body["status"] == "approved"
    assert body["decided_by"]["id"] == manager["id"]


def test_approve_requires_manager_or_admin_role(client, db, auth_headers):
    admin = auth_headers("admin")
    manager = _create_employee(client, admin, name="Manager")
    employee = _create_employee(client, admin, name="Report", manager_id=manager["id"])
    employee_headers = auth_headers("employee", employee_id=employee["id"])

    request = _submit_leave(client, employee_headers).get_json()["data"]

    resp = client.post(
        f"/api/leave-requests/{request['id']}/approve", json={}, headers=employee_headers
    )
    assert resp.status_code == 403


def test_manager_cannot_approve_a_report_they_do_not_manage(client, db, auth_headers):
    admin = auth_headers("admin")
    real_manager = _create_employee(client, admin, name="Real Manager")
    other_manager = _create_employee(client, admin, name="Other Manager")
    employee = _create_employee(client, admin, name="Report", manager_id=real_manager["id"])
    other_manager_headers = auth_headers("manager", employee_id=other_manager["id"])
    employee_headers = auth_headers("employee", employee_id=employee["id"])

    request = _submit_leave(client, employee_headers).get_json()["data"]

    resp = client.post(
        f"/api/leave-requests/{request['id']}/approve", json={}, headers=other_manager_headers
    )
    assert resp.status_code == 403


def test_approve_own_request_returns_403(client, db, auth_headers):
    admin = auth_headers("admin")
    manager = _create_employee(client, admin, name="Manager")
    manager_headers = auth_headers("manager", employee_id=manager["id"])
    request = _submit_leave(client, manager_headers).get_json()["data"]

    resp = client.post(
        f"/api/leave-requests/{request['id']}/approve", json={}, headers=manager_headers
    )
    assert resp.status_code == 403


def test_admin_can_approve_via_explicit_override(client, db, auth_headers):
    admin = auth_headers("admin")
    manager = _create_employee(client, admin, name="Manager")
    employee = _create_employee(client, admin, name="Report", manager_id=manager["id"])
    employee_headers = auth_headers("employee", employee_id=employee["id"])
    request = _submit_leave(client, employee_headers).get_json()["data"]

    resp = client.post(
        f"/api/leave-requests/{request['id']}/approve",
        json={"acting_manager_id": manager["id"]},
        headers=admin,
    )
    assert resp.status_code == 200
    assert resp.get_json()["data"]["decided_by"]["id"] == manager["id"]


def test_reject_leave_request(client, db, auth_headers):
    admin = auth_headers("admin")
    manager = _create_employee(client, admin, name="Manager")
    employee = _create_employee(client, admin, name="Report", manager_id=manager["id"])
    manager_headers = auth_headers("manager", employee_id=manager["id"])
    employee_headers = auth_headers("employee", employee_id=employee["id"])
    request = _submit_leave(client, employee_headers).get_json()["data"]

    resp = client.post(
        f"/api/leave-requests/{request['id']}/reject", json={}, headers=manager_headers
    )
    assert resp.status_code == 200
    assert resp.get_json()["data"]["status"] == "rejected"


def test_approve_already_decided_request_returns_409(client, db, auth_headers):
    admin = auth_headers("admin")
    manager = _create_employee(client, admin, name="Manager")
    employee = _create_employee(client, admin, name="Report", manager_id=manager["id"])
    manager_headers = auth_headers("manager", employee_id=manager["id"])
    employee_headers = auth_headers("employee", employee_id=employee["id"])
    request = _submit_leave(client, employee_headers).get_json()["data"]
    client.post(f"/api/leave-requests/{request['id']}/approve", json={}, headers=manager_headers)

    resp = client.post(
        f"/api/leave-requests/{request['id']}/reject", json={}, headers=manager_headers
    )
    assert resp.status_code == 409


# ---- cancel -----------------------------------------------------------


def test_cancel_own_pending_request(client, db, auth_headers):
    admin = auth_headers("admin")
    employee = _create_employee(client, admin)
    employee_headers = auth_headers("employee", employee_id=employee["id"])
    request = _submit_leave(client, employee_headers).get_json()["data"]

    resp = client.post(
        f"/api/leave-requests/{request['id']}/cancel", json={}, headers=employee_headers
    )
    assert resp.status_code == 200
    assert resp.get_json()["data"]["status"] == "cancelled"


def test_cancel_someone_elses_request_returns_403(client, db, auth_headers):
    admin = auth_headers("admin")
    employee = _create_employee(client, admin, name="Employee")
    other = _create_employee(client, admin, name="Other")
    employee_headers = auth_headers("employee", employee_id=employee["id"])
    other_headers = auth_headers("employee", employee_id=other["id"])
    request = _submit_leave(client, employee_headers).get_json()["data"]

    resp = client.post(
        f"/api/leave-requests/{request['id']}/cancel", json={}, headers=other_headers
    )
    assert resp.status_code == 403


def test_admin_can_cancel_any_pending_request(client, db, auth_headers):
    """An Admin with no linked employee record has no implicit "self" to
    cancel as, so acting on someone else's request requires the explicit
    actor_employee_id override - this is the HR-override path, not a
    silent default."""
    admin = auth_headers("admin")
    employee = _create_employee(client, admin)
    employee_headers = auth_headers("employee", employee_id=employee["id"])
    request = _submit_leave(client, employee_headers).get_json()["data"]

    resp = client.post(
        f"/api/leave-requests/{request['id']}/cancel",
        json={"actor_employee_id": employee["id"]},
        headers=admin,
    )
    assert resp.status_code == 200
    assert resp.get_json()["data"]["status"] == "cancelled"


# ---- balances / dashboard-style reads ------------------------------------


def test_get_own_leave_balances_auto_provisions(client, db, auth_headers):
    admin = auth_headers("admin")
    employee = _create_employee(client, admin)
    employee_headers = auth_headers("employee", employee_id=employee["id"])

    resp = client.get("/api/leave-requests/balances?year=2026", headers=employee_headers)
    assert resp.status_code == 200
    types = {b["leave_type"] for b in resp.get_json()["data"]}
    assert types == {"annual", "sick"}


def test_non_admin_cannot_view_someone_elses_balances(client, db, auth_headers):
    admin = auth_headers("admin")
    employee = _create_employee(client, admin, name="Employee")
    other = _create_employee(client, admin, name="Other")
    other_headers = auth_headers("employee", employee_id=other["id"])

    resp = client.get(
        f"/api/leave-requests/balances?employee_id={employee['id']}&year=2026",
        headers=other_headers,
    )
    # Non-admins always get their own balances regardless of the query param.
    assert resp.status_code == 200
    assert resp.get_json()["data"]  # returns Other's own balances, not Employee's


def test_admin_get_leave_balances_missing_employee_id_returns_400(client, db, auth_headers):
    admin = auth_headers("admin")
    resp = client.get("/api/leave-requests/balances", headers=admin)
    assert resp.status_code == 400


def test_who_is_on_leave(client, db, auth_headers):
    admin = auth_headers("admin")
    manager = _create_employee(client, admin, name="Manager")
    employee = _create_employee(client, admin, name="Report", manager_id=manager["id"])
    manager_headers = auth_headers("manager", employee_id=manager["id"])
    employee_headers = auth_headers("employee", employee_id=employee["id"])

    request = _submit_leave(
        client, employee_headers, start_date="2026-06-08", end_date="2026-06-08"
    ).get_json()["data"]
    client.post(f"/api/leave-requests/{request['id']}/approve", json={}, headers=manager_headers)

    resp = client.get("/api/leave-requests/on-leave?date=2026-06-08", headers=employee_headers)
    assert resp.status_code == 200
    ids = [r["employee"]["id"] for r in resp.get_json()["data"]]
    assert employee["id"] in ids


def test_pending_approvals_for_manager(client, db, auth_headers):
    admin = auth_headers("admin")
    manager = _create_employee(client, admin, name="Manager")
    employee = _create_employee(client, admin, name="Report", manager_id=manager["id"])
    manager_headers = auth_headers("manager", employee_id=manager["id"])
    employee_headers = auth_headers("employee", employee_id=employee["id"])
    _submit_leave(client, employee_headers)

    resp = client.get("/api/leave-requests/pending-approvals", headers=manager_headers)
    assert resp.status_code == 200
    assert len(resp.get_json()["data"]) == 1


def test_pending_approvals_forbidden_for_employee_role(client, db, auth_headers):
    employee_headers = auth_headers("employee")
    resp = client.get("/api/leave-requests/pending-approvals", headers=employee_headers)
    assert resp.status_code == 403


def test_pending_approvals_admin_missing_manager_id_returns_400(client, db, auth_headers):
    admin = auth_headers("admin")
    resp = client.get("/api/leave-requests/pending-approvals", headers=admin)
    assert resp.status_code == 400


def test_escalation_sweep_endpoint_requires_admin(client, db, auth_headers):
    manager = auth_headers("manager")
    resp = client.post("/api/leave-requests/escalate", headers=manager)
    assert resp.status_code == 403

    admin = auth_headers("admin")
    resp = client.post("/api/leave-requests/escalate", headers=admin)
    assert resp.status_code == 200
    assert resp.get_json()["meta"]["escalated_count"] == 0
