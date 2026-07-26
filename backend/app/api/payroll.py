from flask import Blueprint, jsonify, request

from app.models import ROLE_ADMIN
from app.schemas.payroll_schema import (
    PayrollEntryListQuerySchema,
    PayrollEntrySchema,
    PayrollGenerateSchema,
    PayrollPeriodListQuerySchema,
    PayrollPeriodSchema,
)
from app.services.payroll_service import PayrollService
from app.utils.auth import current_user, is_admin, login_required, roles_required
from app.utils.errors import ForbiddenError

payroll_bp = Blueprint("payroll", __name__, url_prefix="/api/payroll")

_service = PayrollService()
_generate_schema = PayrollGenerateSchema()
_period_list_query_schema = PayrollPeriodListQuerySchema()
_entry_list_query_schema = PayrollEntryListQuerySchema()
_period_schema = PayrollPeriodSchema()
_period_list_schema = PayrollPeriodSchema(many=True)
_entry_schema = PayrollEntrySchema()
_entry_list_schema = PayrollEntrySchema(many=True)


def _require_self_or_admin(employee_id: int) -> None:
    """Payroll is sensitive: even Managers may only view their own payslips
    through these two endpoints, never anyone else's - only Admin can."""
    if is_admin():
        return
    if current_user().employee_id != employee_id:
        raise ForbiddenError("You may only view your own payslips")


@payroll_bp.post("/generate")
@roles_required(ROLE_ADMIN)
def generate_payroll():
    payload = _generate_schema.load(request.get_json(force=True, silent=True) or {})
    period = _service.generate_payroll(
        payload["year"], payload["month"], generated_by_id=current_user().employee_id
    )
    return jsonify(data=_period_schema.dump(period)), 201


@payroll_bp.post("/periods/<int:period_id>/finalize")
@roles_required(ROLE_ADMIN)
def finalize_payroll(period_id: int):
    period = _service.finalize_payroll(period_id)
    return jsonify(data=_period_schema.dump(period)), 200


@payroll_bp.get("/periods")
@roles_required(ROLE_ADMIN)
def list_periods():
    filters = _period_list_query_schema.load(request.args.to_dict())
    items, total = _service.list_periods(**filters)
    return (
        jsonify(
            data=_period_list_schema.dump(items),
            meta={"total": total, "page": filters["page"], "per_page": filters["per_page"]},
        ),
        200,
    )


@payroll_bp.get("/periods/<int:period_id>")
@roles_required(ROLE_ADMIN)
def get_period(period_id: int):
    period = _service.get_period(period_id)
    return jsonify(data=_period_schema.dump(period)), 200


@payroll_bp.get("/periods/<int:period_id>/entries")
@roles_required(ROLE_ADMIN)
def list_entries(period_id: int):
    filters = _entry_list_query_schema.load(request.args.to_dict())
    entries = _service.list_entries(period_id, **filters)
    return jsonify(data=_entry_list_schema.dump(entries)), 200


@payroll_bp.get("/periods/<int:period_id>/entries/<int:employee_id>")
@login_required
def get_payslip(period_id: int, employee_id: int):
    _require_self_or_admin(employee_id)
    entry = _service.get_payslip(period_id, employee_id)
    return jsonify(data=_entry_schema.dump(entry)), 200


@payroll_bp.get("/employees/<int:employee_id>/entries")
@login_required
def list_entries_for_employee(employee_id: int):
    _require_self_or_admin(employee_id)
    entries = _service.list_entries_for_employee(employee_id)
    return jsonify(data=_entry_list_schema.dump(entries)), 200
