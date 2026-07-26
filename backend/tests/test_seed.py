from app.models import Employee, LeaveRequest, PayrollEntry, PayrollPeriod, Team, User
from app.seed import run_seed_demo


def test_run_seed_demo_populates_expected_data(db):
    run_seed_demo()

    assert db.session.query(Team).count() == 2
    assert db.session.query(Employee).count() == 7
    assert db.session.query(Employee).filter_by(is_active=False).count() == 1
    assert db.session.query(User).count() == 4  # admin isn't created by this command
    assert db.session.query(LeaveRequest).count() == 4
    assert db.session.query(PayrollPeriod).count() == 1
    assert db.session.query(PayrollEntry).count() == 7

    period = db.session.query(PayrollPeriod).first()
    assert period.status.value == "finalized"


def test_run_seed_demo_is_safe_to_run_twice(db):
    run_seed_demo()
    run_seed_demo()  # should detect existing data and skip, not duplicate

    assert db.session.query(Team).count() == 2
    assert db.session.query(Employee).count() == 7
