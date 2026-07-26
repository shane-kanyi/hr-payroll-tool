from datetime import date

import pytest

from app.models import Team, Employee, EmploymentType
from app.services.employee_service import EmployeeService
from app.utils.errors import ConflictError, NotFoundError, ValidationError


def _employee_data(**overrides):
    data = {
        "name": "Jane Doe",
        "role": "Engineer",
        "team_id": None,
        "manager_id": None,
        "start_date": date(2025, 1, 1),
        "salary": "5000.00",
        "employment_type": "full_time",
    }
    data.update(overrides)
    return data


def test_create_employee_persists_and_converts_employment_type(db):
    service = EmployeeService()
    employee = service.create_employee(_employee_data())

    assert employee.id is not None
    assert employee.employment_type == EmploymentType.FULL_TIME
    assert db.session.get(Employee, employee.id) is not None


def test_create_employee_rejects_unknown_team(db):
    service = EmployeeService()
    with pytest.raises(ValidationError):
        service.create_employee(_employee_data(team_id=999))


def test_create_employee_rejects_unknown_manager(db):
    service = EmployeeService()
    with pytest.raises(ValidationError):
        service.create_employee(_employee_data(manager_id=999))


def test_create_employee_rejects_inactive_manager(db):
    service = EmployeeService()
    manager = service.create_employee(_employee_data(name="Manager Mike"))
    manager.deactivate()
    db.session.commit()

    with pytest.raises(ValidationError):
        service.create_employee(_employee_data(name="Report Rita", manager_id=manager.id))


def test_update_employee_cannot_set_self_as_manager(db):
    service = EmployeeService()
    employee = service.create_employee(_employee_data())

    with pytest.raises(ValidationError):
        service.update_employee(employee.id, {"manager_id": employee.id})


def test_update_employee_rejects_circular_reporting_chain(db):
    """
    A -> manager B -> manager C. Attempting to set C's manager to A should
    be rejected, since that would close the loop A -> B -> C -> A.
    """
    service = EmployeeService()
    a = service.create_employee(_employee_data(name="A"))
    b = service.create_employee(_employee_data(name="B", manager_id=a.id))
    c = service.create_employee(_employee_data(name="C", manager_id=b.id))

    with pytest.raises(ValidationError):
        service.update_employee(a.id, {"manager_id": c.id})

    refreshed_a = service.get_employee(a.id)
    assert refreshed_a.manager_id is None


def test_update_employee_allows_valid_manager_reassignment(db):
    service = EmployeeService()
    old_manager = service.create_employee(_employee_data(name="Old Manager"))
    new_manager = service.create_employee(_employee_data(name="New Manager"))
    employee = service.create_employee(
        _employee_data(name="Employee", manager_id=old_manager.id)
    )

    updated = service.update_employee(employee.id, {"manager_id": new_manager.id})
    assert updated.manager_id == new_manager.id


def test_deactivate_employee_blocked_while_managing_active_reports(db):
    service = EmployeeService()
    manager = service.create_employee(_employee_data(name="Manager"))
    service.create_employee(_employee_data(name="Report", manager_id=manager.id))

    with pytest.raises(ConflictError):
        service.deactivate_employee(manager.id)

    assert service.get_employee(manager.id).is_active is True


def test_deactivate_employee_succeeds_after_reports_reassigned(db):
    service = EmployeeService()
    manager = service.create_employee(_employee_data(name="Manager"))
    other_manager = service.create_employee(_employee_data(name="Other Manager"))
    report = service.create_employee(_employee_data(name="Report", manager_id=manager.id))

    service.update_employee(report.id, {"manager_id": other_manager.id})
    deactivated = service.deactivate_employee(manager.id)

    assert deactivated.is_active is False
    assert deactivated.deactivated_at is not None


def test_deactivate_employee_never_hard_deletes(db):
    service = EmployeeService()
    employee = service.create_employee(_employee_data())
    employee_id = employee.id

    service.deactivate_employee(employee_id)

    assert db.session.get(Employee, employee_id) is not None


def test_deactivate_already_inactive_employee_raises_conflict(db):
    service = EmployeeService()
    employee = service.create_employee(_employee_data())
    service.deactivate_employee(employee.id)

    with pytest.raises(ConflictError):
        service.deactivate_employee(employee.id)


def test_reactivate_employee(db):
    service = EmployeeService()
    employee = service.create_employee(_employee_data())
    service.deactivate_employee(employee.id)

    reactivated = service.reactivate_employee(employee.id)
    assert reactivated.is_active is True
    assert reactivated.deactivated_at is None


def test_get_employee_raises_not_found(db):
    service = EmployeeService()
    with pytest.raises(NotFoundError):
        service.get_employee(999)


def test_list_employees_filters_by_active_status(db):
    service = EmployeeService()
    active = service.create_employee(_employee_data(name="Active Amy"))
    inactive = service.create_employee(_employee_data(name="Inactive Ian"))
    service.deactivate_employee(inactive.id)

    items, total = service.list_employees(is_active=True)
    ids = {e.id for e in items}
    assert active.id in ids
    assert inactive.id not in ids
    assert total == 1


def test_list_employees_search_by_name(db):
    service = EmployeeService()
    service.create_employee(_employee_data(name="Alice Anderson"))
    service.create_employee(_employee_data(name="Bob Brown"))

    items, total = service.list_employees(search="ali")
    assert total == 1
    assert items[0].name == "Alice Anderson"


def test_list_employees_pagination(db):
    service = EmployeeService()
    for i in range(5):
        service.create_employee(_employee_data(name=f"Employee {i}"))

    items, total = service.list_employees(page=1, per_page=2)
    assert total == 5
    assert len(items) == 2


def test_org_chart_builds_correct_tree(db):
    service = EmployeeService()
    ceo = service.create_employee(_employee_data(name="CEO"))
    vp = service.create_employee(_employee_data(name="VP", manager_id=ceo.id))
    service.create_employee(_employee_data(name="IC", manager_id=vp.id))

    tree = service.get_org_chart()

    assert len(tree) == 1
    root = tree[0]
    assert root["name"] == "CEO"
    assert len(root["children"]) == 1
    assert root["children"][0]["name"] == "VP"
    assert root["children"][0]["children"][0]["name"] == "IC"


def test_org_chart_excludes_inactive_by_default(db):
    service = EmployeeService()
    active = service.create_employee(_employee_data(name="Active"))
    inactive = service.create_employee(_employee_data(name="Inactive"))
    service.deactivate_employee(inactive.id)

    tree = service.get_org_chart()
    names = {node["name"] for node in tree}
    assert "Active" in names
    assert "Inactive" not in names
