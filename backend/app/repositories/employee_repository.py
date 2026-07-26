from __future__ import annotations

from app.extensions import db
from app.models import Employee


class EmployeeRepository:
    def __init__(self, session=None):
        self.session = session or db.session

    def get_by_id(self, employee_id: int) -> Employee | None:
        return self.session.get(Employee, employee_id)

    def list(
        self,
        *,
        is_active: bool | None = None,
        team_id: int | None = None,
        manager_id: int | None = None,
        search: str | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[Employee], int]:
        """Returns (items, total_count) for the given filters."""
        query = self.session.query(Employee)

        if is_active is not None:
            query = query.filter(Employee.is_active == is_active)
        if team_id is not None:
            query = query.filter(Employee.team_id == team_id)
        if manager_id is not None:
            query = query.filter(Employee.manager_id == manager_id)
        if search:
            query = query.filter(Employee.name.ilike(f"%{search}%"))

        total = query.count()
        items = (
            query.order_by(Employee.name)
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        return items, total

    def get_by_team(self, team_id: int, active_only: bool = True) -> list[Employee]:
        query = self.session.query(Employee).filter(Employee.team_id == team_id)
        if active_only:
            query = query.filter(Employee.is_active.is_(True))
        return query.order_by(Employee.name).all()

    def get_direct_reports(self, employee_id: int, active_only: bool = True) -> list[Employee]:
        query = self.session.query(Employee).filter(Employee.manager_id == employee_id)
        if active_only:
            query = query.filter(Employee.is_active.is_(True))
        return query.order_by(Employee.name).all()

    def get_all(self, active_only: bool = True) -> list[Employee]:
        query = self.session.query(Employee)
        if active_only:
            query = query.filter(Employee.is_active.is_(True))
        return query.order_by(Employee.name).all()

    def add(self, employee: Employee) -> Employee:
        self.session.add(employee)
        return employee