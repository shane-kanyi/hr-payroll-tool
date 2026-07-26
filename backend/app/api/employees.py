from flask import Blueprint, jsonify, request

from app.models import ROLE_ADMIN
from app.schemas.employee_schema import (
    EmployeeCreateSchema,
    EmployeeListQuerySchema,
    EmployeeSchema,
    EmployeeUpdateSchema,
)
from app.services.employee_service import EmployeeService
from app.utils.auth import login_required, roles_required

employees_bp = Blueprint("employees", __name__, url_prefix="/api/employees")

_service = EmployeeService()
_create_schema = EmployeeCreateSchema()
_update_schema = EmployeeUpdateSchema()
_query_schema = EmployeeListQuerySchema()
_schema = EmployeeSchema()
_list_schema = EmployeeSchema(many=True)


@employees_bp.get("")
@login_required
def list_employees():
    filters = _query_schema.load(request.args.to_dict())
    items, total = _service.list_employees(**filters)
    return (
        jsonify(
            data=_list_schema.dump(items),
            meta={
                "total": total,
                "page": filters["page"],
                "per_page": filters["per_page"],
            },
        ),
        200,
    )


@employees_bp.get("/org-chart")
@login_required
def org_chart():
    include_inactive = request.args.get("include_inactive", "false").lower() in (
        "1",
        "true",
        "yes",
    )
    tree = _service.get_org_chart(include_inactive=include_inactive)
    return jsonify(data=tree), 200


@employees_bp.get("/<int:employee_id>")
@login_required
def get_employee(employee_id: int):
    employee = _service.get_employee(employee_id)
    return jsonify(data=_schema.dump(employee)), 200


@employees_bp.post("")
@roles_required(ROLE_ADMIN)
def create_employee():
    payload = _create_schema.load(request.get_json(force=True, silent=True) or {})
    employee = _service.create_employee(payload)
    return jsonify(data=_schema.dump(employee)), 201


@employees_bp.put("/<int:employee_id>")
@roles_required(ROLE_ADMIN)
def update_employee(employee_id: int):
    payload = _update_schema.load(request.get_json(force=True, silent=True) or {})
    employee = _service.update_employee(employee_id, payload)
    return jsonify(data=_schema.dump(employee)), 200


@employees_bp.post("/<int:employee_id>/deactivate")
@roles_required(ROLE_ADMIN)
def deactivate_employee(employee_id: int):
    employee = _service.deactivate_employee(employee_id)
    return jsonify(data=_schema.dump(employee)), 200


@employees_bp.post("/<int:employee_id>/reactivate")
@roles_required(ROLE_ADMIN)
def reactivate_employee(employee_id: int):
    employee = _service.reactivate_employee(employee_id)
    return jsonify(data=_schema.dump(employee)), 200