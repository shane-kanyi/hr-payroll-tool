from datetime import date, datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import (
    Team,
    Employee,
    EmploymentType,
    Role,
    User,
    LeaveRequest,
    LeaveBalance,
    LeaveType,
    LeaveStatus,
    PayrollPeriod,
    PayrollEntry,
    PayrollPeriodStatus,
    AuditLog,
)


def _make_employee(db, name="Jane Doe", manager=None, team=None, salary="5000.00"):
    employee = Employee(
        name=name,
        role="Engineer",
        team=team,
        manager=manager,
        start_date=date(2025, 1, 1),
        salary=salary,
        employment_type=EmploymentType.FULL_TIME,
    )
    db.session.add(employee)
    db.session.commit()
    return employee


def test_employee_team_and_manager_relationships(db):
    team = Team(name="Platform")
    db.session.add(team)
    db.session.commit()

    manager = _make_employee(db, name="Manager Mike", team=team)
    report = _make_employee(db, name="Report Rita", team=team, manager=manager)

    assert report.manager_id == manager.id
    assert report in manager.direct_reports
    assert report.team_id == team.id
    assert manager in team.employees or report in team.employees


def test_employee_deactivate_is_soft_delete(db):
    employee = _make_employee(db)
    assert employee.is_active is True
    assert employee.deactivated_at is None

    employee.deactivate()
    db.session.commit()

    refreshed = db.session.get(Employee, employee.id)
    assert refreshed.is_active is False
    assert refreshed.deactivated_at is not None
    assert db.session.get(Employee, employee.id) is not None


def test_employee_salary_check_constraint_rejects_negative(db):
    employee = Employee(
        name="Bad Salary",
        role="Engineer",
        start_date=date(2025, 1, 1),
        salary="-100.00",
        employment_type=EmploymentType.FULL_TIME,
    )
    db.session.add(employee)
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_leave_request_end_before_start_is_rejected_by_db(db):
    employee = _make_employee(db)
    bad_request = LeaveRequest(
        employee=employee,
        leave_type=LeaveType.ANNUAL,
        start_date=date(2026, 3, 10),
        end_date=date(2026, 3, 5),
        days_requested="5",
        status=LeaveStatus.PENDING,
        requested_at=datetime.now(timezone.utc),
    )
    db.session.add(bad_request)
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_leave_balance_unique_per_employee_type_year(db):
    employee = _make_employee(db)
    db.session.add(
        LeaveBalance(employee=employee, leave_type=LeaveType.ANNUAL, year=2026,
                     allocated_days="21", used_days="0")
    )
    db.session.commit()

    db.session.add(
        LeaveBalance(employee=employee, leave_type=LeaveType.ANNUAL, year=2026,
                     allocated_days="21", used_days="0")
    )
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_payroll_period_unique_per_year_month(db):
    db.session.add(PayrollPeriod(year=2026, month=7, status=PayrollPeriodStatus.DRAFT))
    db.session.commit()

    db.session.add(PayrollPeriod(year=2026, month=7, status=PayrollPeriodStatus.DRAFT))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_payroll_entry_snapshot_round_trip(db):
    employee = _make_employee(db, salary="6000.00")
    period = PayrollPeriod(year=2026, month=7, status=PayrollPeriodStatus.DRAFT)
    db.session.add(period)
    db.session.commit()

    entry = PayrollEntry(
        period=period,
        employee=employee,
        gross_salary="6000.00",
        unpaid_leave_days="1",
        unpaid_leave_deduction="200.00",
        taxable_income="5800.00",
        tax_deduction="580.00",
        social_security_deduction="348.00",
        net_salary="4872.00",
        calculation_notes={"tax_bracket": "standard", "proration_factor": 1.0},
    )
    db.session.add(entry)
    db.session.commit()

    fetched = db.session.get(PayrollEntry, entry.id)
    assert fetched.net_salary == pytest.approx(4872.00)
    assert fetched.calculation_notes["tax_bracket"] == "standard"
    assert fetched.employee_id == employee.id


def test_role_and_user_relationship(db):
    role = Role(name="manager")
    employee = _make_employee(db)
    db.session.add(role)
    db.session.commit()

    user = User(email="jane@example.com", password_hash="not-a-real-hash",
                employee=employee, role=role)
    db.session.add(user)
    db.session.commit()

    assert user in role.users
    assert user.employee_id == employee.id


def test_audit_log_is_append_only_shape(db):
    role = Role(name="admin")
    employee = _make_employee(db)
    db.session.add(role)
    db.session.commit()
    user = User(email="admin@example.com", password_hash="x", role=role)
    db.session.add(user)
    db.session.commit()

    log = AuditLog(
        actor_user_id=user.id,
        action="employee.deactivated",
        entity_type="employee",
        entity_id=employee.id,
        extra_data={"reason": "resignation"},
    )
    db.session.add(log)
    db.session.commit()

    fetched = db.session.get(AuditLog, log.id)
    assert fetched.action == "employee.deactivated"
    assert fetched.extra_data["reason"] == "resignation"