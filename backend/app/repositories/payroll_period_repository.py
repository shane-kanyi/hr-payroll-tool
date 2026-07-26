from __future__ import annotations

from app.extensions import db
from app.models import PayrollPeriod


class PayrollPeriodRepository:
    def __init__(self, session=None):
        self.session = session or db.session

    def get_by_id(self, period_id: int) -> PayrollPeriod | None:
        return self.session.get(PayrollPeriod, period_id)

    def get_by_year_month(self, year: int, month: int) -> PayrollPeriod | None:
        return (
            self.session.query(PayrollPeriod)
            .filter(PayrollPeriod.year == year, PayrollPeriod.month == month)
            .first()
        )

    def list(self, *, page: int = 1, per_page: int = 20) -> tuple[list[PayrollPeriod], int]:
        query = self.session.query(PayrollPeriod)
        total = query.count()
        items = (
            query.order_by(PayrollPeriod.year.desc(), PayrollPeriod.month.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        return items, total

    def add(self, period: PayrollPeriod) -> PayrollPeriod:
        self.session.add(period)
        return period
