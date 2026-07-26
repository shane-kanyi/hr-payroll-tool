from __future__ import annotations

from datetime import date, datetime

from app.extensions import db
from app.models import LeaveRequest, LeaveStatus, LeaveType


class LeaveRequestRepository:
    def __init__(self, session=None):
        self.session = session or db.session

    def get_by_id(self, request_id: int) -> LeaveRequest | None:
        return self.session.get(LeaveRequest, request_id)

    def add(self, leave_request: LeaveRequest) -> LeaveRequest:
        self.session.add(leave_request)
        return leave_request

    def list_overlapping_for_employee(
        self,
        employee_id: int,
        start_date: date,
        end_date: date,
        *,
        statuses: tuple[LeaveStatus, ...] = (LeaveStatus.PENDING, LeaveStatus.APPROVED),
        exclude_id: int | None = None,
    ) -> list[LeaveRequest]:
        query = self.session.query(LeaveRequest).filter(
            LeaveRequest.employee_id == employee_id,
            LeaveRequest.status.in_(statuses),
            LeaveRequest.start_date <= end_date,
            LeaveRequest.end_date >= start_date,
        )
        if exclude_id is not None:
            query = query.filter(LeaveRequest.id != exclude_id)
        return query.all()

    def list_approved_overlapping_for_team(
        self,
        team_employee_ids: list[int],
        start_date: date,
        end_date: date,
        *,
        exclude_id: int | None = None,
    ) -> list[LeaveRequest]:
        if not team_employee_ids:
            return []
        query = self.session.query(LeaveRequest).filter(
            LeaveRequest.employee_id.in_(team_employee_ids),
            LeaveRequest.status == LeaveStatus.APPROVED,
            LeaveRequest.start_date <= end_date,
            LeaveRequest.end_date >= start_date,
        )
        if exclude_id is not None:
            query = query.filter(LeaveRequest.id != exclude_id)
        return query.all()

    def list_approved_for_employee_in_range(
        self,
        employee_id: int,
        start_date: date,
        end_date: date,
        *,
        leave_type: LeaveType | None = None,
    ) -> list[LeaveRequest]:
        query = self.session.query(LeaveRequest).filter(
            LeaveRequest.employee_id == employee_id,
            LeaveRequest.status == LeaveStatus.APPROVED,
            LeaveRequest.start_date <= end_date,
            LeaveRequest.end_date >= start_date,
        )
        if leave_type is not None:
            query = query.filter(LeaveRequest.leave_type == leave_type)
        return query.all()

    def list_for_employees(
        self,
        employee_ids: list[int],
        *,
        status: LeaveStatus | None = None,
        escalated_only: bool = False,
    ) -> list[LeaveRequest]:
        if not employee_ids:
            return []
        query = self.session.query(LeaveRequest).filter(
            LeaveRequest.employee_id.in_(employee_ids)
        )
        if status is not None:
            query = query.filter(LeaveRequest.status == status)
        if escalated_only:
            query = query.filter(LeaveRequest.escalated_at.isnot(None))
        return query.order_by(LeaveRequest.requested_at).all()

    def list_stale_pending(self, cutoff: datetime) -> list[LeaveRequest]:
        return (
            self.session.query(LeaveRequest)
            .filter(
                LeaveRequest.status == LeaveStatus.PENDING,
                LeaveRequest.escalated_at.is_(None),
                LeaveRequest.requested_at <= cutoff,
            )
            .all()
        )

    def list_on_leave_on(self, on_date: date) -> list[LeaveRequest]:
        return (
            self.session.query(LeaveRequest)
            .filter(
                LeaveRequest.status == LeaveStatus.APPROVED,
                LeaveRequest.start_date <= on_date,
                LeaveRequest.end_date >= on_date,
            )
            .all()
        )

    def list(
        self,
        *,
        employee_id: int | None = None,
        manager_id: int | None = None,
        status: LeaveStatus | None = None,
        escalated_only: bool = False,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[LeaveRequest], int]:
        query = self.session.query(LeaveRequest)

        if employee_id is not None:
            query = query.filter(LeaveRequest.employee_id == employee_id)
        if status is not None:
            query = query.filter(LeaveRequest.status == status)
        if escalated_only:
            query = query.filter(LeaveRequest.escalated_at.isnot(None))
        if manager_id is not None:
            from app.models import Employee

            query = query.join(Employee, LeaveRequest.employee_id == Employee.id).filter(
                Employee.manager_id == manager_id
            )

        total = query.count()
        items = (
            query.order_by(LeaveRequest.requested_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        return items, total
