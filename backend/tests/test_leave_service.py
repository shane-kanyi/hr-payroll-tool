from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.models import Employee, EmploymentType, LeaveBalance, LeaveStatus, LeaveType, Team
from app.services.employee_service import EmployeeService
from app.services.leave_service import LeaveService
from app.utils.errors import ConflictError, ForbiddenError, NotFoundError, ValidationError


def _dt(y, m, d):
    return datetime(y, m, d, tzinfo=timezone.utc)


def _employee_data(**overrides):
    data = {
        "name": "Employee",
        "role": "Engineer",
        "team_id": None,
        "manager_id": None,
        "start_date": date(2020, 1, 1),
        "salary": "5000.00",
        "employment_type": "full_time",
    }
    data.update(overrides)
    return data


@pytest.fixture()
def emp_service():
    return EmployeeService()


@pytest.fixture()
def leave_service():
    return LeaveService()


# A fixed Monday, so "3 business days notice" math is deterministic
# regardless of when tests happen to run.
SUBMIT_NOW = _dt(2026, 6, 1)  # Monday


def _submit(leave_service, employee, *, leave_type="annual", start=None, end=None, now=SUBMIT_NOW, reason=None):
    start = start or date(2026, 6, 8)  # following Monday - respects notice period
    end = end or start
    return leave_service.submit_leave_request(
        {
            "employee_id": employee.id,
            "leave_type": leave_type,
            "start_date": start,
            "end_date": end,
            "reason": reason,
        },
        now=now,
    )


# ---- submission: validation ------------------------------------------


def test_submit_leave_request_happy_path(db, emp_service, leave_service):
    employee = emp_service.create_employee(_employee_data())
    request = _submit(leave_service, employee)

    assert request.id is not None
    assert request.status == LeaveStatus.PENDING
    assert request.days_requested == Decimal("1")


def test_submit_leave_request_rejects_inactive_employee(db, emp_service, leave_service):
    employee = emp_service.create_employee(_employee_data())
    emp_service.deactivate_employee(employee.id)

    with pytest.raises(ValidationError):
        _submit(leave_service, employee)


def test_submit_leave_request_unknown_employee_raises_not_found(db, leave_service):
    with pytest.raises(NotFoundError):
        leave_service.submit_leave_request(
            {
                "employee_id": 999,
                "leave_type": "annual",
                "start_date": date(2026, 6, 8),
                "end_date": date(2026, 6, 8),
            },
            now=SUBMIT_NOW,
        )


def test_submit_leave_request_end_before_start_rejected(db, emp_service, leave_service):
    employee = emp_service.create_employee(_employee_data())
    with pytest.raises(ValidationError):
        _submit(leave_service, employee, start=date(2026, 6, 10), end=date(2026, 6, 8))


def test_submit_leave_request_rejects_cross_year_span(db, emp_service, leave_service):
    employee = emp_service.create_employee(_employee_data())
    with pytest.raises(ValidationError):
        _submit(
            leave_service, employee,
            start=date(2026, 12, 29), end=date(2027, 1, 2),
        )


def test_submit_leave_request_rejects_weekend_only_range(db, emp_service, leave_service):
    employee = emp_service.create_employee(_employee_data())
    # 2026-06-13 and 06-14 are a Saturday/Sunday.
    with pytest.raises(ValidationError):
        _submit(leave_service, employee, start=date(2026, 6, 13), end=date(2026, 6, 14))


# ---- notice period (annual only) --------------------------------------


def test_annual_leave_requires_minimum_notice(db, emp_service, leave_service):
    employee = emp_service.create_employee(_employee_data())
    # Submitting Monday 2026-06-01 for the very next day is far under 3
    # business days notice.
    with pytest.raises(ValidationError):
        _submit(leave_service, employee, start=date(2026, 6, 2), end=date(2026, 6, 2))


def test_annual_leave_exactly_at_minimum_notice_is_accepted(db, emp_service, leave_service):
    employee = emp_service.create_employee(_employee_data())
    # Mon 06-01 + 3 business days = Thu 06-04.
    request = _submit(leave_service, employee, start=date(2026, 6, 4), end=date(2026, 6, 4))
    assert request.status == LeaveStatus.PENDING


def test_sick_leave_exempt_from_notice_period(db, emp_service, leave_service):
    employee = emp_service.create_employee(_employee_data())
    request = _submit(
        leave_service, employee, leave_type="sick",
        start=date(2026, 6, 2), end=date(2026, 6, 2),
    )
    assert request.status == LeaveStatus.PENDING


def test_unpaid_leave_exempt_from_notice_period(db, emp_service, leave_service):
    employee = emp_service.create_employee(_employee_data())
    request = _submit(
        leave_service, employee, leave_type="unpaid",
        start=date(2026, 6, 2), end=date(2026, 6, 2),
    )
    assert request.status == LeaveStatus.PENDING


# ---- overlap detection --------------------------------------------------


def test_overlapping_pending_request_rejected(db, emp_service, leave_service):
    employee = emp_service.create_employee(_employee_data())
    _submit(leave_service, employee, start=date(2026, 6, 8), end=date(2026, 6, 10))

    with pytest.raises(ConflictError):
        _submit(leave_service, employee, start=date(2026, 6, 9), end=date(2026, 6, 11))


def test_adjacent_non_overlapping_requests_allowed(db, emp_service, leave_service):
    employee = emp_service.create_employee(_employee_data())
    _submit(leave_service, employee, start=date(2026, 6, 8), end=date(2026, 6, 9))
    request = _submit(leave_service, employee, start=date(2026, 6, 10), end=date(2026, 6, 11))
    assert request.status == LeaveStatus.PENDING


def test_overlap_ignores_rejected_requests(db, emp_service, leave_service):
    employee = emp_service.create_employee(_employee_data())
    first = _submit(leave_service, employee, start=date(2026, 6, 8), end=date(2026, 6, 9))
    manager = emp_service.create_employee(_employee_data(name="Boss"))
    emp_service.update_employee(employee.id, {"manager_id": manager.id})
    leave_service.reject_leave_request(first.id, manager.id)

    request = _submit(leave_service, employee, start=date(2026, 6, 8), end=date(2026, 6, 9))
    assert request.status == LeaveStatus.PENDING


# ---- balance validation --------------------------------------------------


def test_annual_leave_blocked_when_balance_insufficient(db, emp_service, leave_service):
    employee = emp_service.create_employee(_employee_data(start_date=date(2020, 1, 1)))
    # Drain the balance directly to simulate an employee who has already
    # used up their annual allocation for the year.
    balances = leave_service.get_leave_balances(employee.id, year=2026)
    annual = next(b for b in balances if b.leave_type == LeaveType.ANNUAL)
    annual.used_days = annual.allocated_days
    db.session.commit()

    with pytest.raises(ValidationError):
        _submit(leave_service, employee, start=date(2026, 6, 8), end=date(2026, 6, 8))


def test_unpaid_leave_never_blocked_by_balance(db, emp_service, leave_service):
    employee = emp_service.create_employee(_employee_data())
    # Ask for far more days than any balance would allow.
    request = _submit(
        leave_service, employee, leave_type="unpaid",
        start=date(2026, 6, 8), end=date(2026, 6, 30),
    )
    assert request.status == LeaveStatus.PENDING


def test_new_joiner_gets_prorated_annual_balance(db, emp_service, leave_service):
    # Joins exactly halfway through the year -> ~half the annual allocation.
    employee = emp_service.create_employee(_employee_data(start_date=date(2026, 7, 2)))
    balances = leave_service.get_leave_balances(employee.id, year=2026)
    annual = next(b for b in balances if b.leave_type == LeaveType.ANNUAL)

    assert Decimal("10") < annual.allocated_days < Decimal("11")


def test_employee_not_yet_hired_in_year_gets_zero_allocation(db, emp_service, leave_service):
    employee = emp_service.create_employee(_employee_data(start_date=date(2027, 1, 1)))
    balances = leave_service.get_leave_balances(employee.id, year=2026)
    annual = next(b for b in balances if b.leave_type == LeaveType.ANNUAL)
    assert annual.allocated_days == Decimal("0.00")


# ---- approval workflow: self-approval / authorization -------------------


def test_manager_cannot_approve_own_request(db, emp_service, leave_service):
    manager = emp_service.create_employee(_employee_data(name="Manager"))
    request = _submit(leave_service, manager)

    with pytest.raises(ForbiddenError):
        leave_service.approve_leave_request(request.id, manager.id)


def test_non_manager_cannot_approve_request(db, emp_service, leave_service):
    manager = emp_service.create_employee(_employee_data(name="Manager"))
    employee = emp_service.create_employee(_employee_data(name="Report", manager_id=manager.id))
    stranger = emp_service.create_employee(_employee_data(name="Stranger"))
    request = _submit(leave_service, employee)

    with pytest.raises(ForbiddenError):
        leave_service.approve_leave_request(request.id, stranger.id)


def test_direct_manager_can_approve_request(db, emp_service, leave_service):
    manager = emp_service.create_employee(_employee_data(name="Manager"))
    employee = emp_service.create_employee(_employee_data(name="Report", manager_id=manager.id))
    request = _submit(leave_service, employee)

    approved = leave_service.approve_leave_request(request.id, manager.id, notes="enjoy!")
    assert approved.status == LeaveStatus.APPROVED
    assert approved.decided_by_id == manager.id
    assert approved.decision_notes == "enjoy!"


def test_orphan_employee_with_no_manager_blocks_ordinary_approvers(db, emp_service, leave_service):
    """An employee with no manager anywhere in the chain has no one with
    standing to decide their request - not even another employee picked at
    random. This is exactly what the Admin bypass_authorization override
    (Phase 6 RBAC) exists to resolve; see the next test."""
    employee = emp_service.create_employee(_employee_data(name="No Manager"))
    bystander = emp_service.create_employee(_employee_data(name="Bystander"))
    request = _submit(leave_service, employee)

    with pytest.raises(ForbiddenError):
        leave_service.approve_leave_request(request.id, bystander.id)


def test_admin_bypass_authorization_can_decide_orphan_employee_request(
    db, emp_service, leave_service
):
    employee = emp_service.create_employee(_employee_data(name="No Manager"))
    admin_employee = emp_service.create_employee(_employee_data(name="Admin Employee"))
    request = _submit(leave_service, employee)

    approved = leave_service.approve_leave_request(
        request.id, admin_employee.id, bypass_authorization=True
    )
    assert approved.status == LeaveStatus.APPROVED


def test_cannot_decide_already_decided_request(db, emp_service, leave_service):
    manager = emp_service.create_employee(_employee_data(name="Manager"))
    employee = emp_service.create_employee(_employee_data(name="Report", manager_id=manager.id))
    request = _submit(leave_service, employee)
    leave_service.approve_leave_request(request.id, manager.id)

    with pytest.raises(ConflictError):
        leave_service.approve_leave_request(request.id, manager.id)


def test_reject_sets_status_and_decision_metadata(db, emp_service, leave_service):
    manager = emp_service.create_employee(_employee_data(name="Manager"))
    employee = emp_service.create_employee(_employee_data(name="Report", manager_id=manager.id))
    request = _submit(leave_service, employee)

    rejected = leave_service.reject_leave_request(request.id, manager.id, notes="too busy")
    assert rejected.status == LeaveStatus.REJECTED
    assert rejected.decision_notes == "too busy"


# ---- approval workflow: balance deduction on approval -------------------


def test_approving_annual_leave_deducts_balance(db, emp_service, leave_service):
    manager = emp_service.create_employee(_employee_data(name="Manager"))
    employee = emp_service.create_employee(_employee_data(name="Report", manager_id=manager.id))
    request = _submit(leave_service, employee, start=date(2026, 6, 8), end=date(2026, 6, 9))

    leave_service.approve_leave_request(request.id, manager.id)

    balances = leave_service.get_leave_balances(employee.id, year=2026)
    annual = next(b for b in balances if b.leave_type == LeaveType.ANNUAL)
    assert annual.used_days == Decimal("2")


def test_rejecting_leave_does_not_deduct_balance(db, emp_service, leave_service):
    manager = emp_service.create_employee(_employee_data(name="Manager"))
    employee = emp_service.create_employee(_employee_data(name="Report", manager_id=manager.id))
    request = _submit(leave_service, employee)

    leave_service.reject_leave_request(request.id, manager.id)

    balances = leave_service.get_leave_balances(employee.id, year=2026)
    annual = next(b for b in balances if b.leave_type == LeaveType.ANNUAL)
    assert annual.used_days == Decimal("0.00")


# ---- approval workflow: re-checked overlap and coverage at decision time --


def test_approval_blocked_if_another_request_approved_in_the_meantime(db, emp_service, leave_service):
    manager = emp_service.create_employee(_employee_data(name="Manager"))
    employee = emp_service.create_employee(_employee_data(name="Report", manager_id=manager.id))

    # Two non-overlapping-at-submission-time requests that later collide
    # would be unrealistic here since overlap is blocked at submission for
    # the *same* employee; instead simulate the race by approving one and
    # trying to force-approve a manually crafted overlapping pending one.
    first = _submit(leave_service, employee, start=date(2026, 6, 8), end=date(2026, 6, 9))
    leave_service.approve_leave_request(first.id, manager.id)

    from app.models import LeaveRequest
    second = LeaveRequest(
        employee_id=employee.id,
        leave_type=LeaveType.ANNUAL,
        start_date=date(2026, 6, 9),
        end_date=date(2026, 6, 10),
        days_requested=Decimal("2"),
        status=LeaveStatus.PENDING,
        requested_at=SUBMIT_NOW,
    )
    db.session.add(second)
    db.session.commit()

    with pytest.raises(ConflictError):
        leave_service.approve_leave_request(second.id, manager.id)


def test_team_coverage_blocks_approval_when_majority_would_be_out(db, emp_service, leave_service):
    team = Team(name="Small Team")
    db.session.add(team)
    db.session.commit()

    manager = emp_service.create_employee(_employee_data(name="Manager", team_id=team.id))
    a = emp_service.create_employee(
        _employee_data(name="A", team_id=team.id, manager_id=manager.id)
    )
    b = emp_service.create_employee(
        _employee_data(name="B", team_id=team.id, manager_id=manager.id)
    )
    # 3-person team (manager + A + B). One approved absence already covers
    # the same days for A - approving B too would leave only 1/3 available,
    # below the 50% minimum coverage ratio.
    req_a = _submit(leave_service, a, start=date(2026, 6, 8), end=date(2026, 6, 9))
    leave_service.approve_leave_request(req_a.id, manager.id)

    req_b = _submit(leave_service, b, start=date(2026, 6, 8), end=date(2026, 6, 9))
    with pytest.raises(ConflictError):
        leave_service.approve_leave_request(req_b.id, manager.id)


def test_team_coverage_check_skipped_for_solo_member_team(db, emp_service, leave_service):
    team = Team(name="Solo Team")
    db.session.add(team)
    db.session.commit()

    manager = emp_service.create_employee(_employee_data(name="Manager"))
    solo = emp_service.create_employee(
        _employee_data(name="Solo", team_id=team.id, manager_id=manager.id)
    )
    request = _submit(leave_service, solo)

    approved = leave_service.approve_leave_request(request.id, manager.id)
    assert approved.status == LeaveStatus.APPROVED


# ---- cancellation ---------------------------------------------------------


def test_requester_can_cancel_own_pending_request(db, emp_service, leave_service):
    employee = emp_service.create_employee(_employee_data())
    request = _submit(leave_service, employee)

    cancelled = leave_service.cancel_leave_request(request.id, employee.id)
    assert cancelled.status == LeaveStatus.CANCELLED


def test_others_cannot_cancel_someone_elses_request(db, emp_service, leave_service):
    employee = emp_service.create_employee(_employee_data())
    other = emp_service.create_employee(_employee_data(name="Other"))
    request = _submit(leave_service, employee)

    with pytest.raises(ForbiddenError):
        leave_service.cancel_leave_request(request.id, other.id)


def test_admin_bypass_ownership_can_cancel_someone_elses_request(db, emp_service, leave_service):
    employee = emp_service.create_employee(_employee_data())
    admin_employee = emp_service.create_employee(_employee_data(name="Admin Employee"))
    request = _submit(leave_service, employee)

    cancelled = leave_service.cancel_leave_request(
        request.id, admin_employee.id, bypass_ownership=True
    )
    assert cancelled.status == LeaveStatus.CANCELLED


def test_cannot_cancel_already_decided_request(db, emp_service, leave_service):
    manager = emp_service.create_employee(_employee_data(name="Manager"))
    employee = emp_service.create_employee(_employee_data(name="Report", manager_id=manager.id))
    request = _submit(leave_service, employee)
    leave_service.approve_leave_request(request.id, manager.id)

    with pytest.raises(ConflictError):
        leave_service.cancel_leave_request(request.id, employee.id)


# ---- escalation -------------------------------------------------------


def test_escalation_sweep_flags_stale_pending_requests(db, emp_service, leave_service):
    employee = emp_service.create_employee(_employee_data())
    request = _submit(leave_service, employee, now=_dt(2026, 6, 1))

    escalated = leave_service.run_escalation_sweep(now=_dt(2026, 6, 5))
    assert request.id in [r.id for r in escalated]
    assert request.escalated_at is not None


def test_escalation_sweep_ignores_recent_pending_requests(db, emp_service, leave_service):
    employee = emp_service.create_employee(_employee_data())
    request = _submit(leave_service, employee, leave_type="sick", now=_dt(2026, 6, 4))

    escalated = leave_service.run_escalation_sweep(now=_dt(2026, 6, 5))
    assert request.id not in [r.id for r in escalated]
    assert request.escalated_at is None


def test_escalation_sweep_ignores_already_decided_requests(db, emp_service, leave_service):
    manager = emp_service.create_employee(_employee_data(name="Manager"))
    employee = emp_service.create_employee(_employee_data(name="Report", manager_id=manager.id))
    request = _submit(leave_service, employee, now=_dt(2026, 6, 1))
    leave_service.approve_leave_request(request.id, manager.id)

    escalated = leave_service.run_escalation_sweep(now=_dt(2026, 6, 5))
    assert request.id not in [r.id for r in escalated]


def test_skip_level_manager_can_decide_escalated_request(db, emp_service, leave_service):
    grand_manager = emp_service.create_employee(_employee_data(name="Grand Manager"))
    manager = emp_service.create_employee(
        _employee_data(name="Manager", manager_id=grand_manager.id)
    )
    employee = emp_service.create_employee(
        _employee_data(name="Report", manager_id=manager.id)
    )
    request = _submit(leave_service, employee, now=_dt(2026, 6, 1))

    # Not escalated yet - grand manager isn't authorized.
    with pytest.raises(ForbiddenError):
        leave_service.approve_leave_request(request.id, grand_manager.id)

    leave_service.run_escalation_sweep(now=_dt(2026, 6, 5))

    approved = leave_service.approve_leave_request(request.id, grand_manager.id)
    assert approved.status == LeaveStatus.APPROVED
    assert approved.decided_by_id == grand_manager.id


def test_pending_approvals_for_manager_includes_escalated_skip_level(db, emp_service, leave_service):
    grand_manager = emp_service.create_employee(_employee_data(name="Grand Manager"))
    manager = emp_service.create_employee(
        _employee_data(name="Manager", manager_id=grand_manager.id)
    )
    employee = emp_service.create_employee(
        _employee_data(name="Report", manager_id=manager.id)
    )
    request = _submit(leave_service, employee, now=_dt(2026, 6, 1))

    assert leave_service.list_pending_approvals_for_manager(grand_manager.id) == []

    leave_service.run_escalation_sweep(now=_dt(2026, 6, 5))

    pending = leave_service.list_pending_approvals_for_manager(grand_manager.id)
    assert [r.id for r in pending] == [request.id]


# ---- payroll integration helper ----------------------------------------


def test_get_unpaid_leave_days_for_period_clips_to_period_boundaries(db, emp_service, leave_service):
    manager = emp_service.create_employee(_employee_data(name="Manager"))
    employee = emp_service.create_employee(_employee_data(name="Report", manager_id=manager.id))
    # Unpaid leave straddling a payroll period boundary (end of June into July).
    request = _submit(
        leave_service, employee, leave_type="unpaid",
        start=date(2026, 6, 29), end=date(2026, 7, 2),
    )
    leave_service.approve_leave_request(request.id, manager.id)

    june_days = leave_service.get_unpaid_leave_days_for_period(
        employee.id, date(2026, 6, 1), date(2026, 6, 30)
    )
    july_days = leave_service.get_unpaid_leave_days_for_period(
        employee.id, date(2026, 7, 1), date(2026, 7, 31)
    )

    # Mon 06-29, Tue 06-30 fall in June; Wed 07-01, Thu 07-02 fall in July.
    assert june_days == Decimal("2")
    assert july_days == Decimal("2")


def test_get_unpaid_leave_days_ignores_pending_and_rejected(db, emp_service, leave_service):
    employee = emp_service.create_employee(_employee_data())
    _submit(
        leave_service, employee, leave_type="unpaid",
        start=date(2026, 6, 8), end=date(2026, 6, 9),
    )

    days = leave_service.get_unpaid_leave_days_for_period(
        employee.id, date(2026, 6, 1), date(2026, 6, 30)
    )
    assert days == Decimal("0")


def test_get_unpaid_leave_days_ignores_annual_and_sick(db, emp_service, leave_service):
    manager = emp_service.create_employee(_employee_data(name="Manager"))
    employee = emp_service.create_employee(_employee_data(name="Report", manager_id=manager.id))
    request = _submit(leave_service, employee, start=date(2026, 6, 8), end=date(2026, 6, 9))
    leave_service.approve_leave_request(request.id, manager.id)

    days = leave_service.get_unpaid_leave_days_for_period(
        employee.id, date(2026, 6, 1), date(2026, 6, 30)
    )
    assert days == Decimal("0")
