from __future__ import annotations

from app.extensions import db
from app.models import PayrollEntry


class PayrollEntryRepository:
    def __init__(self, session=None):
        self.session = session or db.session

    def get_by_id(self, entry_id: int) -> PayrollEntry | None:
        return self.session.get(PayrollEntry, entry_id)

    def get_for_period_and_employee(
        self, period_id: int, employee_id: int
    ) -> PayrollEntry | None:
        return (
            self.session.query(PayrollEntry)
            .filter(
                PayrollEntry.payroll_period_id == period_id,
                PayrollEntry.employee_id == employee_id,
            )
            .first()
        )

    def list_for_period(
        self, period_id: int, *, employee_id: int | None = None
    ) -> list[PayrollEntry]:
        query = self.session.query(PayrollEntry).filter(
            PayrollEntry.payroll_period_id == period_id
        )
        if employee_id is not None:
            query = query.filter(PayrollEntry.employee_id == employee_id)
        return query.all()

    def list_for_employee(self, employee_id: int) -> list[PayrollEntry]:
        return (
            self.session.query(PayrollEntry)
            .filter(PayrollEntry.employee_id == employee_id)
            .all()
        )

    def delete_all_for_period(self, period_id: int) -> None:
        self.session.query(PayrollEntry).filter(
            PayrollEntry.payroll_period_id == period_id
        ).delete(synchronize_session=False)

    def add(self, entry: PayrollEntry) -> PayrollEntry:
        self.session.add(entry)
        return entry
