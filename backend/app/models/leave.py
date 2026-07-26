import enum

from app.extensions import db
from app.models.mixins import TimestampMixin


class LeaveType(str, enum.Enum):
    ANNUAL = "annual"
    SICK = "sick"
    UNPAID = "unpaid"


class LeaveStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class LeaveRequest(db.Model, TimestampMixin):
    __tablename__ = "leave_requests"

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(
        db.Integer, db.ForeignKey("employees.id"), nullable=False
    )
    leave_type = db.Column(db.Enum(LeaveType, name="leave_type"), nullable=False)

    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    days_requested = db.Column(db.Numeric(5, 2), nullable=False)

    status = db.Column(
        db.Enum(LeaveStatus, name="leave_status"),
        nullable=False,
        default=LeaveStatus.PENDING,
    )
    reason = db.Column(db.Text, nullable=True)

    requested_at = db.Column(db.DateTime(timezone=True), nullable=False)
    decided_by_id = db.Column(
        db.Integer, db.ForeignKey("employees.id"), nullable=True
    )
    decided_at = db.Column(db.DateTime(timezone=True), nullable=True)
    decision_notes = db.Column(db.Text, nullable=True)

    # Set once a PENDING request has sat unresolved past the escalation
    # threshold. From that point on the requester's skip-level manager may
    # also decide it, in addition to their direct manager. See LeaveService.
    escalated_at = db.Column(db.DateTime(timezone=True), nullable=True)

    employee = db.relationship(
        "Employee", back_populates="leave_requests", foreign_keys=[employee_id]
    )
    decided_by = db.relationship("Employee", foreign_keys=[decided_by_id])

    __table_args__ = (
        db.CheckConstraint("end_date >= start_date", name="ck_leave_end_after_start"),
        db.CheckConstraint("days_requested > 0", name="ck_leave_days_positive"),
        db.Index("ix_leave_requests_employee_id", "employee_id"),
        db.Index("ix_leave_requests_status", "status"),
        db.Index(
            "ix_leave_requests_employee_dates", "employee_id", "start_date", "end_date"
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<LeaveRequest {self.id} employee={self.employee_id} "
            f"{self.start_date}..{self.end_date} status={self.status}>"
        )


class LeaveBalance(db.Model, TimestampMixin):
    __tablename__ = "leave_balances"

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(
        db.Integer, db.ForeignKey("employees.id"), nullable=False
    )
    leave_type = db.Column(db.Enum(LeaveType, name="leave_type"), nullable=False)
    year = db.Column(db.Integer, nullable=False)

    allocated_days = db.Column(db.Numeric(5, 2), nullable=False, default=0)
    used_days = db.Column(db.Numeric(5, 2), nullable=False, default=0)

    employee = db.relationship("Employee", back_populates="leave_balances")

    __table_args__ = (
        db.UniqueConstraint(
            "employee_id", "leave_type", "year", name="uq_leave_balance_employee_type_year"
        ),
        db.CheckConstraint("allocated_days >= 0", name="ck_leave_balance_allocated_non_negative"),
        db.CheckConstraint("used_days >= 0", name="ck_leave_balance_used_non_negative"),
    )

    @property
    def remaining_days(self):
        return self.allocated_days - self.used_days

    def __repr__(self) -> str:
        return (
            f"<LeaveBalance employee={self.employee_id} {self.leave_type} "
            f"{self.year} {self.used_days}/{self.allocated_days}>"
        )