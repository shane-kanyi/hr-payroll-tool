from __future__ import annotations

import calendar
from datetime import date, datetime, timezone
from decimal import ROUND_HALF_UP, Decimal

from flask import current_app

from app.extensions import db
from app.models import Employee, PayrollEntry, PayrollPeriod, PayrollPeriodStatus
from app.repositories.employee_repository import EmployeeRepository
from app.repositories.payroll_entry_repository import PayrollEntryRepository
from app.repositories.payroll_period_repository import PayrollPeriodRepository
from app.services.leave_service import LeaveService
from app.utils.dates import count_business_days
from app.utils.errors import ConflictError, NotFoundError, ValidationError
from app.utils.tax import calculate_progressive_tax

_CENTS = Decimal("0.01")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(_CENTS, rounding=ROUND_HALF_UP)


class PayrollService:
    def __init__(
        self,
        period_repo: PayrollPeriodRepository | None = None,
        entry_repo: PayrollEntryRepository | None = None,
        employee_repo: EmployeeRepository | None = None,
        leave_service: LeaveService | None = None,
    ):
        self.period_repo = period_repo or PayrollPeriodRepository()
        self.entry_repo = entry_repo or PayrollEntryRepository()
        self.employee_repo = employee_repo or EmployeeRepository()
        self.leave_service = leave_service or LeaveService()

    # ---- reads -------------------------------------------------------

    def get_period(self, period_id: int) -> PayrollPeriod:
        period = self.period_repo.get_by_id(period_id)
        if period is None:
            raise NotFoundError(f"Payroll period {period_id} not found")
        return period

    def get_period_by_year_month(self, year: int, month: int) -> PayrollPeriod:
        period = self.period_repo.get_by_year_month(year, month)
        if period is None:
            raise NotFoundError(f"Payroll period {year}-{month:02d} not found")
        return period

    def list_periods(self, *, page: int = 1, per_page: int = 20) -> tuple[list[PayrollPeriod], int]:
        return self.period_repo.list(page=page, per_page=per_page)

    def list_entries(
        self, period_id: int, *, employee_id: int | None = None
    ) -> list[PayrollEntry]:
        self.get_period(period_id)  # 404 if the period doesn't exist
        return self.entry_repo.list_for_period(period_id, employee_id=employee_id)

    def get_payslip(self, period_id: int, employee_id: int) -> PayrollEntry:
        entry = self.entry_repo.get_for_period_and_employee(period_id, employee_id)
        if entry is None:
            raise NotFoundError(
                f"No payslip for employee {employee_id} in payroll period {period_id}"
            )
        return entry

    def list_entries_for_employee(self, employee_id: int) -> list[PayrollEntry]:
        return self.entry_repo.list_for_employee(employee_id)

    # ---- writes: generate / finalize -----------------------------------

    def generate_payroll(
        self,
        year: int,
        month: int,
        *,
        generated_by_id: int | None = None,
        now: datetime | None = None,
    ) -> PayrollPeriod:
        now = now or _utcnow()
        period = self.period_repo.get_by_year_month(year, month)

        if period is not None and period.status == PayrollPeriodStatus.FINALIZED:
            raise ConflictError(
                f"Payroll period {year}-{month:02d} is already finalized and cannot be "
                "regenerated. Historical payroll is immutable by design."
            )

        if period is None:
            period = PayrollPeriod(year=year, month=month, status=PayrollPeriodStatus.DRAFT)
            self.period_repo.add(period)
            db.session.flush()
        else:
            # Still DRAFT: this is a preview state, so a re-run recomputes
            # from scratch (e.g. a leave request got approved since the
            # last preview) rather than layering on top of stale rows.
            self.entry_repo.delete_all_for_period(period.id)
            db.session.flush()

        period_start = date(year, month, 1)
        period_end = date(year, month, calendar.monthrange(year, month)[1])
        working_days_in_month = count_business_days(period_start, period_end)

        for employee in self.employee_repo.get_all(active_only=False):
            fields = self._calculate_entry(employee, period_start, period_end, working_days_in_month)
            if fields is None:
                continue  # not employed at any point during this period
            entry = PayrollEntry(
                payroll_period_id=period.id,
                employee_id=employee.id,
                **fields,
            )
            self.entry_repo.add(entry)

        period.generated_at = now
        period.generated_by_id = generated_by_id
        db.session.commit()
        return period

    def finalize_payroll(self, period_id: int, *, now: datetime | None = None) -> PayrollPeriod:
        period = self.get_period(period_id)
        if period.status == PayrollPeriodStatus.FINALIZED:
            raise ConflictError(f"Payroll period {period_id} is already finalized")

        entries = self.entry_repo.list_for_period(period_id)
        if not entries:
            raise ValidationError(
                "Cannot finalize a payroll period with no entries - generate it first"
            )

        period.status = PayrollPeriodStatus.FINALIZED
        period.finalized_at = now or _utcnow()
        db.session.commit()
        return period

    # ---- calculation ----------------------------------------------------

    def _calculate_entry(
        self,
        employee: Employee,
        period_start: date,
        period_end: date,
        working_days_in_month: Decimal,
    ) -> dict | None:
        effective_start = max(period_start, employee.start_date)
        effective_end = period_end

        if not employee.is_active and employee.deactivated_at is not None:
            deactivation_date = employee.deactivated_at.date()
            if deactivation_date < effective_end:
                effective_end = deactivation_date

        if effective_start > effective_end:
            return None  # not employed on any day of this period

        calendar_days_in_period = Decimal((period_end - period_start).days + 1)
        days_employed = Decimal((effective_end - effective_start).days + 1)
        proration_factor = min(days_employed / calendar_days_in_period, Decimal("1"))

        gross_salary = _quantize(employee.salary * proration_factor)

        unpaid_leave_days = self.leave_service.get_unpaid_leave_days_for_period(
            employee.id, period_start, period_end
        )
        daily_rate_for_leave = (
            (employee.salary / working_days_in_month) if working_days_in_month > 0 else Decimal("0")
        )
        unpaid_leave_deduction = _quantize(daily_rate_for_leave * unpaid_leave_days)
        unpaid_leave_deduction = min(unpaid_leave_deduction, gross_salary)

        taxable_income = max(gross_salary - unpaid_leave_deduction, Decimal("0.00"))

        tax_deduction, tax_breakdown = calculate_progressive_tax(taxable_income)

        social_security_rate = Decimal(str(current_app.config.get("SOCIAL_SECURITY_RATE", 0.06)))
        social_security_deduction = _quantize(taxable_income * social_security_rate)

        net_salary = max(
            taxable_income - tax_deduction - social_security_deduction, Decimal("0.00")
        )

        return {
            "gross_salary": gross_salary,
            "unpaid_leave_days": unpaid_leave_days,
            "unpaid_leave_deduction": unpaid_leave_deduction,
            "taxable_income": taxable_income,
            "tax_deduction": tax_deduction,
            "social_security_deduction": social_security_deduction,
            "net_salary": net_salary,
            "calculation_notes": {
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
                "effective_start": effective_start.isoformat(),
                "effective_end": effective_end.isoformat(),
                "calendar_days_in_period": int(calendar_days_in_period),
                "working_days_in_month": str(working_days_in_month),
                "proration_factor": str(proration_factor),
                "daily_rate_for_leave": str(_quantize(daily_rate_for_leave)),
                "social_security_rate": float(social_security_rate),
                "tax_breakdown": tax_breakdown,
            },
        }
