from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from app.models import PayrollPeriodStatus
from app.services.employee_service import EmployeeService
from app.services.leave_service import LeaveService
from app.services.payroll_service import PayrollService
from app.utils.errors import ConflictError, NotFoundError, ValidationError


def _dt(y, m, d):
    return datetime(y, m, d, tzinfo=timezone.utc)


def _employee_data(**overrides):
    data = {
        "name": "Employee",
        "role": "Engineer",
        "team_id": None,
        "manager_id": None,
        "start_date": date(2020, 1, 1),
        "salary": "6000.00",
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


@pytest.fixture()
def payroll_service():
    return PayrollService()


# ---- core calculation: full month, no leave -----------------------------


def test_full_month_active_employee_no_leave(db, emp_service, payroll_service):
    employee = emp_service.create_employee(_employee_data(salary="6000.00"))

    period = payroll_service.generate_payroll(2026, 7)
    entries = payroll_service.list_entries(period.id)

    assert len(entries) == 1
    entry = entries[0]
    assert entry.gross_salary == Decimal("6000.00")
    assert entry.unpaid_leave_days == Decimal("0")
    assert entry.unpaid_leave_deduction == Decimal("0.00")
    assert entry.taxable_income == Decimal("6000.00")
    assert entry.tax_deduction == Decimal("800.00")  # see docs/PAYROLL.md brackets
    assert entry.social_security_deduction == Decimal("360.00")  # 6% flat
    assert entry.net_salary == Decimal("4840.00")


def test_zero_salary_yields_zero_deductions_and_zero_net(db, emp_service, payroll_service):
    employee = emp_service.create_employee(_employee_data(salary="0.00"))

    period = payroll_service.generate_payroll(2026, 7)
    entry = payroll_service.get_payslip(period.id, employee.id)

    assert entry.gross_salary == Decimal("0.00")
    assert entry.tax_deduction == Decimal("0.00")
    assert entry.social_security_deduction == Decimal("0.00")
    assert entry.net_salary == Decimal("0.00")


def test_salary_near_tax_bracket_boundary_no_cliff(db, emp_service, payroll_service):
    just_under = emp_service.create_employee(_employee_data(name="Under", salary="2999.00"))
    just_over = emp_service.create_employee(_employee_data(name="Over", salary="3001.00"))

    period = payroll_service.generate_payroll(2026, 7)
    entry_under = payroll_service.get_payslip(period.id, just_under.id)
    entry_over = payroll_service.get_payslip(period.id, just_over.id)

    assert entry_under.tax_deduction == Decimal("199.90")
    assert entry_over.tax_deduction == Decimal("200.20")
    # A $2 difference in salary should not translate into a huge tax jump.
    assert (entry_over.tax_deduction - entry_under.tax_deduction) < Decimal("1.00")


# ---- mid-month joiners / leavers -----------------------------------------


def test_mid_month_joiner_prorates_gross_pay(db, emp_service, payroll_service):
    # July 2026 has 31 calendar days; joining on the 16th means 16 days
    # employed (16..31 inclusive) out of 31 -> 3100 * 16/31 = 1600.00 exactly.
    employee = emp_service.create_employee(
        _employee_data(salary="3100.00", start_date=date(2026, 7, 16))
    )

    period = payroll_service.generate_payroll(2026, 7)
    entry = payroll_service.get_payslip(period.id, employee.id)

    assert entry.gross_salary == Decimal("1600.00")
    assert entry.calculation_notes["proration_factor"] == str(Decimal("16") / Decimal("31"))
    assert entry.taxable_income == Decimal("1600.00")
    assert entry.tax_deduction == Decimal("60.00")  # 1000@0 + 600@10%
    assert entry.social_security_deduction == Decimal("96.00")  # 1600 * 6%
    assert entry.net_salary == Decimal("1444.00")


def test_mid_month_deactivation_prorates_gross_pay(db, emp_service, payroll_service):
    employee = emp_service.create_employee(
        _employee_data(salary="3100.00", start_date=date(2020, 1, 1))
    )
    # Deactivate mid-period: last paid day is the 16th, same 16/31 split as
    # the joiner case above, applied symmetrically on exit.
    employee.deactivate()
    employee.deactivated_at = _dt(2026, 7, 16)
    db.session.commit()

    period = payroll_service.generate_payroll(2026, 7)
    entry = payroll_service.get_payslip(period.id, employee.id)

    assert entry.gross_salary == Decimal("1600.00")


def test_employee_deactivated_before_period_is_excluded_entirely(db, emp_service, payroll_service):
    employee = emp_service.create_employee(_employee_data(start_date=date(2020, 1, 1)))
    employee.deactivate()
    employee.deactivated_at = _dt(2026, 6, 15)
    db.session.commit()

    period = payroll_service.generate_payroll(2026, 7)
    entries = payroll_service.list_entries(period.id)

    assert entries == []
    with pytest.raises(NotFoundError):
        payroll_service.get_payslip(period.id, employee.id)


def test_employee_not_yet_hired_is_excluded(db, emp_service, payroll_service):
    emp_service.create_employee(_employee_data(start_date=date(2026, 8, 1)))

    period = payroll_service.generate_payroll(2026, 7)
    assert payroll_service.list_entries(period.id) == []


def test_currently_active_employee_not_yet_started_this_period_excluded_others_included(
    db, emp_service, payroll_service
):
    excluded = emp_service.create_employee(
        _employee_data(name="Future Hire", start_date=date(2026, 8, 1))
    )
    included = emp_service.create_employee(_employee_data(name="Existing"))

    period = payroll_service.generate_payroll(2026, 7)
    entries = payroll_service.list_entries(period.id)
    employee_ids = {e.employee_id for e in entries}

    assert included.id in employee_ids
    assert excluded.id not in employee_ids


# ---- unpaid leave interaction --------------------------------------------


def test_unpaid_leave_reduces_taxable_income_and_net_pay(
    db, emp_service, leave_service, payroll_service
):
    # 2300 / 23 business days in July 2026 = 100.00/day exactly.
    manager = emp_service.create_employee(_employee_data(name="Manager"))
    employee = emp_service.create_employee(
        _employee_data(name="Report", salary="2300.00", manager_id=manager.id)
    )
    request = leave_service.submit_leave_request(
        {
            "employee_id": employee.id,
            "leave_type": "unpaid",
            "start_date": date(2026, 7, 6),
            "end_date": date(2026, 7, 10),
        },
        now=_dt(2026, 6, 1),
    )
    leave_service.approve_leave_request(request.id, manager.id)

    period = payroll_service.generate_payroll(2026, 7)
    entry = payroll_service.get_payslip(period.id, employee.id)

    assert entry.gross_salary == Decimal("2300.00")
    assert entry.unpaid_leave_days == Decimal("5")
    assert entry.unpaid_leave_deduction == Decimal("500.00")
    assert entry.taxable_income == Decimal("1800.00")
    assert entry.tax_deduction == Decimal("80.00")  # 1000@0 + 800@10%
    assert entry.social_security_deduction == Decimal("108.00")  # 1800 * 6%
    assert entry.net_salary == Decimal("1612.00")


def test_full_month_unpaid_leave_yields_zero_net_pay(
    db, emp_service, leave_service, payroll_service
):
    manager = emp_service.create_employee(_employee_data(name="Manager"))
    employee = emp_service.create_employee(
        _employee_data(name="Report", salary="2300.00", manager_id=manager.id)
    )
    request = leave_service.submit_leave_request(
        {
            "employee_id": employee.id,
            "leave_type": "unpaid",
            "start_date": date(2026, 7, 1),
            "end_date": date(2026, 7, 31),
        },
        now=_dt(2026, 6, 1),
    )
    leave_service.approve_leave_request(request.id, manager.id)

    period = payroll_service.generate_payroll(2026, 7)
    entry = payroll_service.get_payslip(period.id, employee.id)

    assert entry.taxable_income == Decimal("0.00")
    assert entry.tax_deduction == Decimal("0.00")
    assert entry.social_security_deduction == Decimal("0.00")
    assert entry.net_salary == Decimal("0.00")


def test_paid_leave_does_not_reduce_gross_pay(db, emp_service, leave_service, payroll_service):
    manager = emp_service.create_employee(_employee_data(name="Manager"))
    employee = emp_service.create_employee(
        _employee_data(name="Report", salary="6000.00", manager_id=manager.id)
    )
    request = leave_service.submit_leave_request(
        {
            "employee_id": employee.id,
            "leave_type": "annual",
            "start_date": date(2026, 7, 6),
            "end_date": date(2026, 7, 10),
        },
        now=_dt(2026, 6, 1),
    )
    leave_service.approve_leave_request(request.id, manager.id)

    period = payroll_service.generate_payroll(2026, 7)
    entry = payroll_service.get_payslip(period.id, employee.id)

    assert entry.unpaid_leave_deduction == Decimal("0.00")
    assert entry.gross_salary == Decimal("6000.00")
    assert entry.net_salary == Decimal("4840.00")


# ---- generate / regenerate / finalize lifecycle --------------------------


def test_regenerating_a_draft_period_recomputes_entries(
    db, emp_service, leave_service, payroll_service
):
    manager = emp_service.create_employee(_employee_data(name="Manager"))
    employee = emp_service.create_employee(
        _employee_data(name="Report", salary="2300.00", manager_id=manager.id)
    )

    period = payroll_service.generate_payroll(2026, 7)
    first_entry = payroll_service.get_payslip(period.id, employee.id)
    assert first_entry.unpaid_leave_deduction == Decimal("0.00")

    # Approve unpaid leave for this employee only *after* the first preview.
    request = leave_service.submit_leave_request(
        {
            "employee_id": employee.id,
            "leave_type": "unpaid",
            "start_date": date(2026, 7, 6),
            "end_date": date(2026, 7, 10),
        },
        now=_dt(2026, 6, 1),
    )
    leave_service.approve_leave_request(request.id, manager.id)

    payroll_service.generate_payroll(2026, 7)
    entries = payroll_service.list_entries(period.id)
    second_entry = payroll_service.get_payslip(period.id, employee.id)

    assert len(entries) == 2  # manager + employee, not duplicated
    assert second_entry.unpaid_leave_deduction == Decimal("500.00")


def test_finalize_locks_period_against_regeneration(db, emp_service, payroll_service):
    emp_service.create_employee(_employee_data())
    period = payroll_service.generate_payroll(2026, 7)

    payroll_service.finalize_payroll(period.id)

    with pytest.raises(ConflictError):
        payroll_service.generate_payroll(2026, 7)


def test_finalizing_twice_raises_conflict(db, emp_service, payroll_service):
    emp_service.create_employee(_employee_data())
    period = payroll_service.generate_payroll(2026, 7)
    payroll_service.finalize_payroll(period.id)

    with pytest.raises(ConflictError):
        payroll_service.finalize_payroll(period.id)


def test_cannot_finalize_period_with_no_entries(db, payroll_service):
    period = payroll_service.generate_payroll(2026, 7)  # no employees at all

    with pytest.raises(ValidationError):
        payroll_service.finalize_payroll(period.id)


def test_get_unknown_period_raises_not_found(db, payroll_service):
    with pytest.raises(NotFoundError):
        payroll_service.get_period(999)


def test_finalized_payroll_is_never_recalculated_even_if_salary_changes_later(
    db, emp_service, payroll_service
):
    employee = emp_service.create_employee(_employee_data(salary="6000.00"))
    period = payroll_service.generate_payroll(2026, 7)
    payroll_service.finalize_payroll(period.id)

    emp_service.update_employee(employee.id, {"salary": "9000.00"})

    entry = payroll_service.get_payslip(period.id, employee.id)
    assert entry.gross_salary == Decimal("6000.00")  # snapshot, untouched
