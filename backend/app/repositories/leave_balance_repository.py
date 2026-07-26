from __future__ import annotations

from app.extensions import db
from app.models import LeaveBalance, LeaveType


class LeaveBalanceRepository:
    def __init__(self, session=None):
        self.session = session or db.session

    def get(self, employee_id: int, leave_type: LeaveType, year: int) -> LeaveBalance | None:
        return (
            self.session.query(LeaveBalance)
            .filter(
                LeaveBalance.employee_id == employee_id,
                LeaveBalance.leave_type == leave_type,
                LeaveBalance.year == year,
            )
            .first()
        )

    def list_for_employee(self, employee_id: int, year: int | None = None) -> list[LeaveBalance]:
        query = self.session.query(LeaveBalance).filter(LeaveBalance.employee_id == employee_id)
        if year is not None:
            query = query.filter(LeaveBalance.year == year)
        return query.order_by(LeaveBalance.year.desc(), LeaveBalance.leave_type).all()

    def add(self, balance: LeaveBalance) -> LeaveBalance:
        self.session.add(balance)
        return balance
