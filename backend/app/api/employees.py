from flask import Blueprint, jsonify, request

from app.schemas.employee_schema import (
    EmployeeCreateSchema,
    EmployeeListQuerySchema,
    EmployeeSchema,
    EmployeeUpdateSchema,
)
from app.services.employee_service import EmployeeService

employees_bp = Blueprint("employees", __name__, url_prefix="/api/employees")

_service = EmployeeService()
_create_schema = EmployeeCreateSchema()
_update_schema = EmployeeUpdateSchema()
_query_schema = EmployeeListQuerySchema()
_schema = EmployeeSchema()
_list_schema = EmployeeSchema(many=True)


@employees_bp.get("")
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
def org_chart():
    include_inactive = request.args.get("include_inactive", "false").lower() in (
        "1",
        "true",
        "yes",
    )
    tree = _service.get_org_chart(include_inactive=include_inactive)
    return jsonify(data=tree), 200


@employees_bp.get("/<int:employee_id>")
def get_employee(employee_id: int):
    employee = _service.get_employee(employee_id)
    return jsonify(data=_schema.dump(employee)), 200


@employees_bp.post("")
def create_employee():
    payload = _create_schema.load(request.get_json(force=True, silent=True) or {})
    employee = _service.create_employee(payload)
    return jsonify(data=_schema.dump(employee)), 201


@employees_bp.put("/<int:employee_id>")
def update_employee(employee_id: int):
    payload = _update_schema.load(request.get_json(force=True, silent=True) or {})
    employee = _service.update_employee(employee_id, payload)
    return jsonify(data=_schema.dump(employee)), 200


@employees_bp.post("/<int:employee_id>/deactivate")
def deactivate_employee(employee_id: int):
    employee = _service.deactivate_employee(employee_id)
    return jsonify(data=_schema.dump(employee)), 200


@employees_bp.post("/<int:employee_id>/reactivate")
def reactivate_employee(employee_id: int):
    employee = _service.reactivate_employee(employee_id)
    return jsonify(data=_schema.dump(employee)), 200