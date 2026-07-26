import enum

from app.extensions import db
from app.models.mixins import TimestampMixin, utcnow


class EmploymentType(str, enum.Enum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"


class Employee(db.Model, TimestampMixin):
    __tablename__ = "employees"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(120), nullable=False)  # job title, not RBAC role
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=True)
    manager_id = db.Column(db.Integer, db.ForeignKey("employees.id"), nullable=True)

    start_date = db.Column(db.Date, nullable=False)
    salary = db.Column(db.Numeric(12, 2), nullable=False)  # monthly gross, in base currency
    employment_type = db.Column(
        db.Enum(EmploymentType, name="employment_type"), nullable=False
    )

    is_active = db.Column(db.Boolean, nullable=False, default=True)
    deactivated_at = db.Column(db.DateTime(timezone=True), nullable=True)

    team = db.relationship("Team", back_populates="employees", foreign_keys=[team_id])
    manager = db.relationship(
        "Employee", remote_side=[id], back_populates="direct_reports"
    )
    direct_reports = db.relationship("Employee", back_populates="manager")

    leave_requests = db.relationship(
        "LeaveRequest",
        back_populates="employee",
        foreign_keys="LeaveRequest.employee_id",
    )
    leave_balances = db.relationship("LeaveBalance", back_populates="employee")
    payroll_entries = db.relationship("PayrollEntry", back_populates="employee")

    __table_args__ = (
        db.CheckConstraint("salary >= 0", name="ck_employee_salary_non_negative"),
        db.Index("ix_employees_manager_id", "manager_id"),
        db.Index("ix_employees_team_id", "team_id"),
        db.Index("ix_employees_is_active", "is_active"),
    )

    def deactivate(self) -> None:
        """Soft-deactivate. Never call db.session.delete() on an Employee."""
        self.is_active = False
        self.deactivated_at = utcnow()

    def reactivate(self) -> None:
        self.is_active = True
        self.deactivated_at = None

    def __repr__(self) -> str:
        return f"<Employee {self.id} {self.name!r}>"