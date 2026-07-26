from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from flask import current_app

from app.extensions import db
from app.models import Employee, LeaveBalance, LeaveRequest, LeaveStatus, LeaveType
from app.repositories.employee_repository import EmployeeRepository
from app.repositories.leave_balance_repository import LeaveBalanceRepository
from app.repositories.leave_request_repository import LeaveRequestRepository
from app.utils.dates import add_business_days, clip_range, count_business_days
from app.utils.errors import ConflictError, ForbiddenError, NotFoundError, ValidationError

# Leave types that draw down an allocated yearly balance. UNPAID is
# deliberately excluded - it has no balance to exhaust, and instead
# reduces the employee's pay for the period (see get_unpaid_leave_days_for_period,
# consumed by the payroll engine in Phase 4).
BALANCE_TRACKED_TYPES = (LeaveType.ANNUAL, LeaveType.SICK)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class LeaveService:
    def __init__(
        self,
        repo: LeaveRequestRepository | None = None,
        balance_repo: LeaveBalanceRepository | None = None,
        employee_repo: EmployeeRepository | None = None,
    ):
        self.repo = repo or LeaveRequestRepository()
        self.balance_repo = balance_repo or LeaveBalanceRepository()
        self.employee_repo = employee_repo or EmployeeRepository()

    # ---- reads -------------------------------------------------------

    def get_leave_request(self, request_id: int) -> LeaveRequest:
        request = self.repo.get_by_id(request_id)
        if request is None:
            raise NotFoundError(f"Leave request {request_id} not found")
        return request

    def list_leave_requests(
        self,
        *,
        employee_id: int | None = None,
        manager_id: int | None = None,
        status: str | LeaveStatus | None = None,
        escalated_only: bool = False,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[LeaveRequest], int]:
        status_enum = LeaveStatus(status) if status and not isinstance(status, LeaveStatus) else status
        return self.repo.list(
            employee_id=employee_id,
            manager_id=manager_id,
            status=status_enum,
            escalated_only=escalated_only,
            page=page,
            per_page=per_page,
        )

    def list_pending_approvals_for_manager(self, manager_id: int) -> list[LeaveRequest]:
        """Pending requests a manager can act on: their direct reports' own
        requests, plus escalated requests from their skip-level (grand-)
        reports that no one has resolved in time."""
        direct_report_ids = [
            e.id for e in self.employee_repo.get_direct_reports(manager_id, active_only=False)
        ]
        skip_level_ids: list[int] = []
        for report_id in direct_report_ids:
            skip_level_ids.extend(
                e.id for e in self.employee_repo.get_direct_reports(report_id, active_only=False)
            )

        direct_pending = self.repo.list_for_employees(direct_report_ids, status=LeaveStatus.PENDING)
        escalated_pending = self.repo.list_for_employees(
            skip_level_ids, status=LeaveStatus.PENDING, escalated_only=True
        )

        combined = {r.id: r for r in direct_pending}
        for r in escalated_pending:
            combined.setdefault(r.id, r)
        return sorted(combined.values(), key=lambda r: r.requested_at)

    def who_is_on_leave(self, on_date: date | None = None) -> list[LeaveRequest]:
        return self.repo.list_on_leave_on(on_date or date.today())

    def get_leave_balances(self, employee_id: int, year: int | None = None) -> list[LeaveBalance]:
        employee = self._get_employee_or_404(employee_id)
        year = year or date.today().year
        for leave_type in BALANCE_TRACKED_TYPES:
            self._get_or_create_balance(employee, leave_type, year)
        db.session.commit()
        return self.balance_repo.list_for_employee(employee_id, year=year)

    def get_unpaid_leave_days_for_period(
        self, employee_id: int, period_start: date, period_end: date
    ) -> Decimal:
        """Business days of APPROVED unpaid leave overlapping a payroll
        period, clipped to the period boundaries. Consumed by the payroll
        engine (Phase 4) to compute unpaid-leave deductions."""
        requests = self.repo.list_approved_for_employee_in_range(
            employee_id, period_start, period_end, leave_type=LeaveType.UNPAID
        )
        total = Decimal("0")
        for request in requests:
            clipped = clip_range(request.start_date, request.end_date, period_start, period_end)
            if clipped:
                total += count_business_days(*clipped)
        return total

    # ---- writes: submit / cancel --------------------------------------

    def submit_leave_request(self, data: dict, *, now: datetime | None = None) -> LeaveRequest:
        now = now or _utcnow()
        today = now.date()

        employee = self.employee_repo.get_by_id(data["employee_id"])
        if employee is None:
            raise NotFoundError(f"Employee {data['employee_id']} not found")
        if not employee.is_active:
            raise ValidationError("Inactive employees cannot submit leave requests")

        leave_type = self._coerce_leave_type(data["leave_type"])
        start_date = data["start_date"]
        end_date = data["end_date"]

        if end_date < start_date:
            raise ValidationError("end_date cannot be before start_date")
        if start_date.year != end_date.year:
            raise ValidationError(
                "A leave request cannot span across a calendar year boundary. "
                "Submit two separate requests, one per year."
            )

        if leave_type == LeaveType.ANNUAL:
            min_notice = int(current_app.config.get("LEAVE_MIN_NOTICE_BUSINESS_DAYS", 3))
            earliest_allowed = add_business_days(today, min_notice)
            if start_date < earliest_allowed:
                raise ValidationError(
                    f"Annual leave requires at least {min_notice} business day(s) notice. "
                    f"Earliest start date accepted today is {earliest_allowed.isoformat()}."
                )

        days_requested = count_business_days(start_date, end_date)
        if days_requested <= 0:
            raise ValidationError(
                "The selected date range contains no business days (weekend-only range)"
            )

        overlapping = self.repo.list_overlapping_for_employee(employee.id, start_date, end_date)
        if overlapping:
            raise ConflictError(
                "This request overlaps an existing pending or approved leave request",
                payload={"conflicting_request_ids": [r.id for r in overlapping]},
            )

        if leave_type in BALANCE_TRACKED_TYPES:
            balance = self._get_or_create_balance(employee, leave_type, start_date.year)
            if balance.remaining_days < days_requested:
                raise ValidationError(
                    f"Insufficient {leave_type.value} leave balance: "
                    f"{balance.remaining_days} day(s) remaining, {days_requested} requested"
                )

        leave_request = LeaveRequest(
            employee_id=employee.id,
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date,
            days_requested=days_requested,
            status=LeaveStatus.PENDING,
            reason=data.get("reason"),
            requested_at=now,
        )
        self.repo.add(leave_request)
        db.session.commit()
        return leave_request

    def cancel_leave_request(
        self, request_id: int, actor_employee_id: int, *, now: datetime | None = None
    ) -> LeaveRequest:
        leave_request = self.get_leave_request(request_id)
        if leave_request.status != LeaveStatus.PENDING:
            raise ConflictError(
                f"Only pending requests can be cancelled (current status: "
                f"{leave_request.status.value})"
            )
        if actor_employee_id != leave_request.employee_id:
            raise ForbiddenError("Only the requester can cancel their own leave request")

        leave_request.status = LeaveStatus.CANCELLED
        db.session.commit()
        return leave_request

    # ---- writes: approve / reject --------------------------------------

    def approve_leave_request(
        self,
        request_id: int,
        acting_manager_id: int,
        *,
        notes: str | None = None,
        now: datetime | None = None,
    ) -> LeaveRequest:
        now = now or _utcnow()
        leave_request, employee = self._prepare_decision(request_id, acting_manager_id)

        still_overlapping = self.repo.list_overlapping_for_employee(
            employee.id,
            leave_request.start_date,
            leave_request.end_date,
            statuses=(LeaveStatus.APPROVED,),
            exclude_id=leave_request.id,
        )
        if still_overlapping:
            raise ConflictError(
                "This request now overlaps a leave request approved in the meantime",
                payload={"conflicting_request_ids": [r.id for r in still_overlapping]},
            )

        self._check_team_coverage(employee, leave_request)

        if leave_request.leave_type in BALANCE_TRACKED_TYPES:
            balance = self._get_or_create_balance(
                employee, leave_request.leave_type, leave_request.start_date.year
            )
            if balance.remaining_days < leave_request.days_requested:
                raise ValidationError(
                    f"Insufficient {leave_request.leave_type.value} leave balance at approval "
                    f"time: {balance.remaining_days} day(s) remaining, "
                    f"{leave_request.days_requested} requested"
                )
            balance.used_days = balance.used_days + leave_request.days_requested

        leave_request.status = LeaveStatus.APPROVED
        leave_request.decided_by_id = acting_manager_id
        leave_request.decided_at = now
        leave_request.decision_notes = notes
        db.session.commit()
        return leave_request

    def reject_leave_request(
        self,
        request_id: int,
        acting_manager_id: int,
        *,
        notes: str | None = None,
        now: datetime | None = None,
    ) -> LeaveRequest:
        now = now or _utcnow()
        leave_request, _employee = self._prepare_decision(request_id, acting_manager_id)

        leave_request.status = LeaveStatus.REJECTED
        leave_request.decided_by_id = acting_manager_id
        leave_request.decided_at = now
        leave_request.decision_notes = notes
        db.session.commit()
        return leave_request

    def _prepare_decision(
        self, request_id: int, acting_manager_id: int
    ) -> tuple[LeaveRequest, Employee]:
        leave_request = self.get_leave_request(request_id)
        if leave_request.status != LeaveStatus.PENDING:
            raise ConflictError(
                f"This leave request has already been decided "
                f"(status: {leave_request.status.value})"
            )

        acting_manager = self.employee_repo.get_by_id(acting_manager_id)
        if acting_manager is None:
            raise NotFoundError(f"Employee {acting_manager_id} not found")
        if not acting_manager.is_active:
            raise ValidationError("Acting manager must be an active employee")

        employee = leave_request.employee
        if acting_manager_id == employee.id:
            raise ForbiddenError("A manager cannot approve or reject their own leave request")

        self._authorize_decision(leave_request, employee, acting_manager_id)
        return leave_request, employee

    def _authorize_decision(
        self, leave_request: LeaveRequest, employee: Employee, acting_manager_id: int
    ) -> None:
        allowed_ids: set[int] = set()
        if employee.manager_id:
            allowed_ids.add(employee.manager_id)
        if leave_request.escalated_at and employee.manager and employee.manager.manager_id:
            allowed_ids.add(employee.manager.manager_id)

        if not allowed_ids:
            # No manager anywhere in the chain to decide this - a request would
            # otherwise be permanently stuck ("insufficient approval handling").
            # Until RBAC (Phase 6) exists to restrict this to Admin-role users,
            # any active employee may act as a fallback approver here.
            return

        if acting_manager_id not in allowed_ids:
            raise ForbiddenError(
                "You are not authorized to decide this leave request. Only the "
                "employee's manager (or, once escalated, their skip-level "
                "manager) may approve or reject it."
            )

    def _check_team_coverage(self, employee: Employee, leave_request: LeaveRequest) -> None:
        if employee.team_id is None:
            return

        team_members = self.employee_repo.get_by_team(employee.team_id, active_only=True)
        team_size = len(team_members)
        if team_size < 2:
            # Nothing to safeguard a solo-member team against - documented gap.
            return

        team_ids = [m.id for m in team_members]
        overlapping = self.repo.list_approved_overlapping_for_team(
            team_ids,
            leave_request.start_date,
            leave_request.end_date,
            exclude_id=leave_request.id,
        )
        on_leave_ids = {r.employee_id for r in overlapping}
        on_leave_ids.add(employee.id)  # this request, if approved

        available_after = team_size - len(on_leave_ids)
        min_ratio = float(current_app.config.get("LEAVE_TEAM_MIN_COVERAGE_RATIO", 0.5))
        if (available_after / team_size) < min_ratio:
            raise ConflictError(
                "Approving this request would leave the team under-covered "
                f"({available_after}/{team_size} available, minimum ratio "
                f"{min_ratio:.0%})",
                payload={
                    "team_id": employee.team_id,
                    "team_size": team_size,
                    "available_after": available_after,
                },
            )

    # ---- escalation ----------------------------------------------------

    def run_escalation_sweep(self, *, now: datetime | None = None) -> list[LeaveRequest]:
        now = now or _utcnow()
        threshold_days = int(current_app.config.get("LEAVE_ESCALATION_THRESHOLD_DAYS", 3))
        cutoff = now - timedelta(days=threshold_days)

        stale = self.repo.list_stale_pending(cutoff)
        for request in stale:
            request.escalated_at = now
        db.session.commit()
        return stale

    # ---- helpers ---------------------------------------------------------

    def _coerce_leave_type(self, value) -> LeaveType:
        return value if isinstance(value, LeaveType) else LeaveType(value)

    def _get_employee_or_404(self, employee_id: int) -> Employee:
        employee = self.employee_repo.get_by_id(employee_id)
        if employee is None:
            raise NotFoundError(f"Employee {employee_id} not found")
        return employee

    def _get_or_create_balance(
        self, employee: Employee, leave_type: LeaveType, year: int
    ) -> LeaveBalance:
        existing = self.balance_repo.get(employee.id, leave_type, year)
        if existing is not None:
            return existing

        allocated = self._prorated_allocation(employee, leave_type, year)
        balance = LeaveBalance(
            employee_id=employee.id,
            leave_type=leave_type,
            year=year,
            allocated_days=allocated,
            used_days=Decimal("0.00"),
        )
        self.balance_repo.add(balance)
        db.session.flush()
        return balance

    def _prorated_allocation(self, employee: Employee, leave_type: LeaveType, year: int) -> Decimal:
        if leave_type == LeaveType.ANNUAL:
            default_days = Decimal(str(current_app.config.get("ANNUAL_LEAVE_DAYS_PER_YEAR", 21)))
        else:
            default_days = Decimal(str(current_app.config.get("SICK_LEAVE_DAYS_PER_YEAR", 10)))

        if employee.start_date.year > year:
            return Decimal("0.00")
        if employee.start_date.year < year:
            return default_days.quantize(Decimal("0.01"))

        year_start = date(year, 1, 1)
        year_end = date(year, 12, 31)
        total_days_in_year = Decimal((year_end - year_start).days + 1)
        remaining_days_in_year = Decimal((year_end - employee.start_date).days + 1)
        return (default_days * remaining_days_in_year / total_days_in_year).quantize(
            Decimal("0.01")
        )
