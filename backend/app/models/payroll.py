import enum

from app.extensions import db
from app.models.mixins import TimestampMixin


class PayrollPeriodStatus(str, enum.Enum):
    DRAFT = "draft"       
    FINALIZED = "finalized"  


class PayrollPeriod(db.Model, TimestampMixin):
    __tablename__ = "payroll_periods"

    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=False)  # 1-12

    status = db.Column(
        db.Enum(PayrollPeriodStatus, name="payroll_period_status"),
        nullable=False,
        default=PayrollPeriodStatus.DRAFT,
    )

    generated_at = db.Column(db.DateTime(timezone=True), nullable=True)
    generated_by_id = db.Column(
        db.Integer, db.ForeignKey("employees.id"), nullable=True
    )
    finalized_at = db.Column(db.DateTime(timezone=True), nullable=True)

    entries = db.relationship("PayrollEntry", back_populates="period")
    generated_by = db.relationship("Employee", foreign_keys=[generated_by_id])

    __table_args__ = (
        db.UniqueConstraint("year", "month", name="uq_payroll_period_year_month"),
        db.CheckConstraint("month >= 1 AND month <= 12", name="ck_payroll_period_month_range"),
    )

    def __repr__(self) -> str:
        return f"<PayrollPeriod {self.year}-{self.month:02d} {self.status}>"


class PayrollEntry(db.Model, TimestampMixin):
    __tablename__ = "payroll_entries"

    id = db.Column(db.Integer, primary_key=True)
    payroll_period_id = db.Column(
        db.Integer, db.ForeignKey("payroll_periods.id"), nullable=False
    )
    employee_id = db.Column(
        db.Integer, db.ForeignKey("employees.id"), nullable=False
    )

    gross_salary = db.Column(db.Numeric(12, 2), nullable=False)
    unpaid_leave_days = db.Column(db.Numeric(5, 2), nullable=False, default=0)
    unpaid_leave_deduction = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    taxable_income = db.Column(db.Numeric(12, 2), nullable=False)
    tax_deduction = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    social_security_deduction = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    net_salary = db.Column(db.Numeric(12, 2), nullable=False)

    calculation_notes = db.Column(db.JSON, nullable=True)

    period = db.relationship("PayrollPeriod", back_populates="entries")
    employee = db.relationship("Employee", back_populates="payroll_entries")

    __table_args__ = (
        db.UniqueConstraint(
            "payroll_period_id", "employee_id", name="uq_payroll_entry_period_employee"
        ),
        db.CheckConstraint("gross_salary >= 0", name="ck_payroll_entry_gross_non_negative"),
        db.CheckConstraint("net_salary >= 0", name="ck_payroll_entry_net_non_negative"),
        db.Index("ix_payroll_entries_employee_id", "employee_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<PayrollEntry period={self.payroll_period_id} "
            f"employee={self.employee_id} net={self.net_salary}>"
        )