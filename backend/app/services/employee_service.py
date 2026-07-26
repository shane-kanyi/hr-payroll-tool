from app.extensions import db
from app.models import Employee, EmploymentType
from app.repositories.employee_repository import EmployeeRepository
from app.repositories.team_repository import TeamRepository
from app.utils.errors import ConflictError, NotFoundError, ValidationError


class EmployeeService:
    def __init__(
        self,
        repo: EmployeeRepository | None = None,
        team_repo: TeamRepository | None = None,
    ):
        self.repo = repo or EmployeeRepository()
        self.team_repo = team_repo or TeamRepository()

    # ---- reads -----------------------------------------------------

    def get_employee(self, employee_id: int) -> Employee:
        employee = self.repo.get_by_id(employee_id)
        if employee is None:
            raise NotFoundError(f"Employee {employee_id} not found")
        return employee

    def list_employees(
        self,
        *,
        is_active: bool | None = None,
        team_id: int | None = None,
        manager_id: int | None = None,
        search: str | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[Employee], int]:
        return self.repo.list(
            is_active=is_active,
            team_id=team_id,
            manager_id=manager_id,
            search=search,
            page=page,
            per_page=per_page,
        )

    def get_org_chart(self, include_inactive: bool = False) -> list[dict]:
        employees = self.repo.get_all(active_only=not include_inactive)
        nodes = {
            e.id: {
                "id": e.id,
                "name": e.name,
                "role": e.role,
                "team": e.team.name if e.team else None,
                "is_active": e.is_active,
                "children": [],
            }
            for e in employees
        }
        roots: list[dict] = []
        for e in employees:
            node = nodes[e.id]
            if e.manager_id and e.manager_id in nodes:
                nodes[e.manager_id]["children"].append(node)
            else:
                roots.append(node)
        return roots

    # ---- writes ------------------------------------------------------

    def create_employee(self, data: dict) -> Employee:
        data = dict(data)
        self._validate_team(data.get("team_id"))
        self._validate_manager(data.get("manager_id"), employee_id=None)
        if "employment_type" in data and not isinstance(data["employment_type"], EmploymentType):
            data["employment_type"] = EmploymentType(data["employment_type"])

        employee = Employee(**data)
        self.repo.add(employee)
        db.session.commit()
        return employee

    def update_employee(self, employee_id: int, data: dict) -> Employee:
        employee = self.get_employee(employee_id)
        data = dict(data)

        if "team_id" in data:
            self._validate_team(data["team_id"])
        if "manager_id" in data:
            self._validate_manager(data["manager_id"], employee_id=employee_id)
        if "employment_type" in data and not isinstance(data["employment_type"], EmploymentType):
            data["employment_type"] = EmploymentType(data["employment_type"])

        for key, value in data.items():
            setattr(employee, key, value)

        db.session.commit()
        return employee

    def deactivate_employee(self, employee_id: int) -> Employee:
        employee = self.get_employee(employee_id)
        if not employee.is_active:
            raise ConflictError(f"Employee {employee_id} is already inactive")

        active_reports = self.repo.get_direct_reports(employee_id, active_only=True)
        if active_reports:
            names = ", ".join(r.name for r in active_reports)
            raise ConflictError(
                f"Cannot deactivate {employee.name}: still the manager of "
                f"{len(active_reports)} active employee(s) ({names}). "
                "Reassign their manager first.",
                payload={"blocking_reports": [r.id for r in active_reports]},
            )

        employee.deactivate()
        db.session.commit()
        return employee

    def reactivate_employee(self, employee_id: int) -> Employee:
        employee = self.get_employee(employee_id)
        if employee.is_active:
            raise ConflictError(f"Employee {employee_id} is already active")
        employee.reactivate()
        db.session.commit()
        return employee

    # ---- validation helpers -------------------------------------------

    def _validate_team(self, team_id: int | None) -> None:
        if team_id is None:
            return
        if self.team_repo.get_by_id(team_id) is None:
            raise ValidationError(f"Team {team_id} does not exist")

    def _validate_manager(self, manager_id: int | None, *, employee_id: int | None) -> None:
        if manager_id is None:
            return

        manager = self.repo.get_by_id(manager_id)
        if manager is None:
            raise ValidationError(f"Manager {manager_id} does not exist")
        if not manager.is_active:
            raise ValidationError(f"Manager {manager_id} is not an active employee")

        if employee_id is None:
            return  # creating a new employee - no existing chain to loop back into

        if manager_id == employee_id:
            raise ValidationError("An employee cannot be their own manager")

        current = manager
        seen: set[int] = set()
        while current is not None:
            if current.id == employee_id:
                raise ValidationError(
                    "Assigning this manager would create a circular reporting chain"
                )
            if current.id in seen:
                break  
            seen.add(current.id)
            current = current.manager