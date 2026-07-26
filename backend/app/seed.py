"""Demo/sample data generator.

Builds a small but realistic dataset - two teams, a manager hierarchy,
an inactive employee (to show soft-delete/history preservation), leave
requests in every status (pending, approved, rejected, escalated), and one
finalized payroll period with an unpaid-leave deduction in it - entirely
through the same service layer the API uses, so every row respects the
same business rules real usage would (balance provisioning, overlap
checks, the payroll formula, etc.) rather than being hand-crafted rows
that could drift out of sync with the rules documented in docs/LEAVE.md
and docs/PAYROLL.md.

Intentionally separate from `flask create-admin` (app/cli.py): that command
is the minimal, security-relevant bootstrap step every environment needs.
This one is optional sample data for local development, demos, and the
SQL dump referenced in the README.
"""

from datetime import date, datetime, timedelta, timezone

import click
from flask import Flask

from app.extensions import db
from app.models import Team
from app.services.auth_service import AuthService
from app.services.employee_service import EmployeeService
from app.services.leave_service import LeaveService
from app.services.payroll_service import PayrollService
from app.utils.dates import add_business_days

DEMO_PASSWORD = "Password123!"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _previous_month(today: date) -> tuple[int, int]:
    if today.month == 1:
        return today.year - 1, 12
    return today.year, today.month - 1


def run_seed_demo() -> None:
    if db.session.query(Team).first() is not None:
        click.echo("Sample data already exists (a team was found) - skipping.")
        return

    today = date.today()
    payroll_year, payroll_month = _previous_month(today)

    employee_service = EmployeeService()
    leave_service = LeaveService()
    payroll_service = PayrollService()
    auth_service = AuthService()

    click.echo("Creating teams...")
    engineering = Team(name="Engineering")
    sales = Team(name="Sales")
    db.session.add_all([engineering, sales])
    db.session.commit()

    click.echo("Creating employees...")
    grace = employee_service.create_employee(
        {
            "name": "Grace Kim",
            "role": "Engineering Manager",
            "team_id": engineering.id,
            "start_date": date(2019, 3, 1),
            "salary": "7000.00",
            "employment_type": "full_time",
        }
    )
    sam = employee_service.create_employee(
        {
            "name": "Sam Patel",
            "role": "Sales Manager",
            "team_id": sales.id,
            "start_date": date(2019, 6, 1),
            "salary": "6500.00",
            "employment_type": "full_time",
        }
    )
    ravi = employee_service.create_employee(
        {
            "name": "Ravi Shah",
            "role": "Software Engineer",
            "team_id": engineering.id,
            "manager_id": grace.id,
            "start_date": date(2021, 9, 15),
            "salary": "4200.00",
            "employment_type": "full_time",
        }
    )
    amara = employee_service.create_employee(
        {
            "name": "Amara Okafor",
            "role": "Software Engineer",
            "team_id": engineering.id,
            "manager_id": grace.id,
            "start_date": date(2022, 1, 10),
            "salary": "3900.00",
            "employment_type": "full_time",
        }
    )
    nina = employee_service.create_employee(
        {
            "name": "Nina Fischer",
            "role": "Contract Designer",
            "team_id": engineering.id,
            "manager_id": grace.id,
            "start_date": date(2023, 4, 1),
            "salary": "2500.00",
            "employment_type": "contract",
        }
    )
    leo = employee_service.create_employee(
        {
            "name": "Leo Martins",
            "role": "Sales Executive",
            "team_id": sales.id,
            "manager_id": sam.id,
            "start_date": date(2020, 11, 1),
            "salary": "3200.00",
            "employment_type": "full_time",
        }
    )
    tom = employee_service.create_employee(
        {
            "name": "Tom Reyes",
            "role": "Sales Executive (former)",
            "team_id": sales.id,
            "manager_id": sam.id,
            "start_date": date(2018, 2, 1),
            "salary": "3000.00",
            "employment_type": "full_time",
        }
    )
    employee_service.deactivate_employee(tom.id)
    click.echo(f"  {7} employees created (Tom Reyes deactivated to demonstrate history preservation)")

    click.echo("Creating login accounts (password for all: %s)..." % DEMO_PASSWORD)
    for email, role, employee in [
        ("grace@example.com", "manager", grace),
        ("sam@example.com", "manager", sam),
        ("ravi@example.com", "employee", ravi),
        ("amara@example.com", "employee", amara),
    ]:
        auth_service.create_user(
            {"email": email, "password": DEMO_PASSWORD, "role": role, "employee_id": employee.id}
        )

    click.echo("Creating leave requests...")
    # Approved annual leave, comfortably past the notice-period minimum.
    ravi_annual_start = add_business_days(today, 5)
    ravi_annual_end = add_business_days(ravi_annual_start, 2)
    ravi_request = leave_service.submit_leave_request(
        {
            "employee_id": ravi.id,
            "leave_type": "annual",
            "start_date": ravi_annual_start,
            "end_date": ravi_annual_end,
            "reason": "Family trip",
        }
    )
    leave_service.approve_leave_request(ravi_request.id, grace.id, notes="Enjoy!")

    # Rejected annual leave.
    nina_start = add_business_days(today, 6)
    nina_request = leave_service.submit_leave_request(
        {
            "employee_id": nina.id,
            "leave_type": "annual",
            "start_date": nina_start,
            "end_date": nina_start,
            "reason": "Long weekend",
        }
    )
    leave_service.reject_leave_request(
        nina_request.id, grace.id, notes="Two others already out that week"
    )

    # Escalated pending request: submitted well before the escalation
    # threshold, then run through the sweep.
    old_now = _utcnow() - timedelta(days=10)
    amara_request = leave_service.submit_leave_request(
        {
            "employee_id": amara.id,
            "leave_type": "sick",
            "start_date": old_now.date() + timedelta(days=1),
            "end_date": old_now.date() + timedelta(days=1),
        },
        now=old_now,
    )
    leave_service.run_escalation_sweep()
    click.echo(f"  Amara's request escalated: {amara_request.escalated_at is not None}")

    # Approved unpaid leave inside last month, so it shows up as a real
    # deduction on the payroll period generated below.
    unpaid_start = date(payroll_year, payroll_month, 8)
    unpaid_end = date(payroll_year, payroll_month, 10)
    leo_request = leave_service.submit_leave_request(
        {
            "employee_id": leo.id,
            "leave_type": "unpaid",
            "start_date": unpaid_start,
            "end_date": unpaid_end,
            "reason": "Unpaid personal leave",
        }
    )
    leave_service.approve_leave_request(leo_request.id, sam.id)

    click.echo(f"Generating and finalizing payroll for {payroll_year}-{payroll_month:02d}...")
    period = payroll_service.generate_payroll(payroll_year, payroll_month, generated_by_id=grace.id)
    payroll_service.finalize_payroll(period.id)

    click.echo("Done. Sample login accounts:")
    click.echo(f"  grace@example.com / {DEMO_PASSWORD}  (manager, manages Ravi/Amara/Nina)")
    click.echo(f"  sam@example.com   / {DEMO_PASSWORD}  (manager, manages Leo/Tom)")
    click.echo(f"  ravi@example.com  / {DEMO_PASSWORD}  (employee)")
    click.echo(f"  amara@example.com / {DEMO_PASSWORD}  (employee, has an escalated pending request)")
    click.echo("  (Admin account: created separately via `flask create-admin`)")


def register_seed_command(app: Flask) -> None:
    @app.cli.command("seed-demo")
    def seed_demo() -> None:
        """Populate the database with sample teams/employees/leave/payroll data."""
        run_seed_demo()
