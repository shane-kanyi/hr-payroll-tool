from datetime import date

from flask import Blueprint, jsonify, request

from app.models import ROLE_ADMIN, ROLE_MANAGER
from app.schemas.leave_schema import (
    LeaveBalanceSchema,
    LeaveCancelSchema,
    LeaveDecisionSchema,
    LeaveRequestCreateSchema,
    LeaveRequestListQuerySchema,
    LeaveRequestSchema,
)
from app.services.leave_service import LeaveService
from app.utils.auth import current_user, is_admin, login_required, roles_required
from app.utils.errors import ForbiddenError, ValidationError

leave_bp = Blueprint("leave_requests", __name__, url_prefix="/api/leave-requests")

_service = LeaveService()
_create_schema = LeaveRequestCreateSchema()
_decision_schema = LeaveDecisionSchema()
_cancel_schema = LeaveCancelSchema()
_query_schema = LeaveRequestListQuerySchema()
_schema = LeaveRequestSchema()
_list_schema = LeaveRequestSchema(many=True)
_balance_list_schema = LeaveBalanceSchema(many=True)


def _own_employee_id() -> int:
    """The logged-in user's linked employee id, or a clear error if none."""
    employee_id = current_user().employee_id
    if employee_id is None:
        raise ValidationError("Your account is not linked to an employee record")
    return employee_id


def _resolve_acting_employee_id(override: int | None) -> int:
    """Admins may act as any employee via an explicit override; everyone
    else always acts as themselves, regardless of what they send."""
    if is_admin() and override is not None:
        return override
    return _own_employee_id()


@leave_bp.get("")
@login_required
def list_leave_requests():
    filters = _query_schema.load(request.args.to_dict())
    if not is_admin():
        # Non-admins can only ever browse their own leave history here.
        filters["employee_id"] = _own_employee_id()
        filters["manager_id"] = None
    items, total = _service.list_leave_requests(**filters)
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


@leave_bp.get("/pending-approvals")
@roles_required(ROLE_ADMIN, ROLE_MANAGER)
def pending_approvals():
    if is_admin():
        manager_id = request.args.get("manager_id", type=int)
        if manager_id is None:
            raise ValidationError("manager_id query parameter is required")
    else:
        manager_id = _own_employee_id()
    items = _service.list_pending_approvals_for_manager(manager_id)
    return jsonify(data=_list_schema.dump(items)), 200


@leave_bp.get("/on-leave")
@login_required
def on_leave():
    raw_date = request.args.get("date")
    on_date = date.fromisoformat(raw_date) if raw_date else None
    items = _service.who_is_on_leave(on_date)
    return jsonify(data=_list_schema.dump(items)), 200


@leave_bp.get("/balances")
@login_required
def leave_balances():
    if is_admin():
        employee_id = request.args.get("employee_id", type=int)
        if employee_id is None:
            raise ValidationError("employee_id query parameter is required")
    else:
        employee_id = _own_employee_id()
    year = request.args.get("year", type=int)
    balances = _service.get_leave_balances(employee_id, year=year)
    return jsonify(data=_balance_list_schema.dump(balances)), 200


@leave_bp.post("/escalate")
@roles_required(ROLE_ADMIN)
def run_escalation_sweep():
    escalated = _service.run_escalation_sweep()
    return jsonify(data=_list_schema.dump(escalated), meta={"escalated_count": len(escalated)}), 200


@leave_bp.get("/<int:request_id>")
@login_required
def get_leave_request(request_id: int):
    leave_request = _service.get_leave_request(request_id)
    user = current_user()
    is_owner = leave_request.employee_id == user.employee_id
    is_their_manager = (
        user.employee_id is not None and leave_request.employee.manager_id == user.employee_id
    )
    if not (is_admin() or is_owner or is_their_manager):
        raise ForbiddenError("You do not have access to this leave request")
    return jsonify(data=_schema.dump(leave_request)), 200


@leave_bp.post("")
@login_required
def submit_leave_request():
    payload = _create_schema.load(request.get_json(force=True, silent=True) or {})
    payload["employee_id"] = _resolve_acting_employee_id(payload.pop("employee_id"))
    leave_request = _service.submit_leave_request(payload)
    return jsonify(data=_schema.dump(leave_request)), 201


@leave_bp.post("/<int:request_id>/approve")
@roles_required(ROLE_ADMIN, ROLE_MANAGER)
def approve_leave_request(request_id: int):
    payload = _decision_schema.load(request.get_json(force=True, silent=True) or {})
    acting_manager_id = _resolve_acting_employee_id(payload.get("acting_manager_id"))
    leave_request = _service.approve_leave_request(
        request_id,
        acting_manager_id,
        notes=payload.get("notes"),
        bypass_authorization=is_admin(),
    )
    return jsonify(data=_schema.dump(leave_request)), 200


@leave_bp.post("/<int:request_id>/reject")
@roles_required(ROLE_ADMIN, ROLE_MANAGER)
def reject_leave_request(request_id: int):
    payload = _decision_schema.load(request.get_json(force=True, silent=True) or {})
    acting_manager_id = _resolve_acting_employee_id(payload.get("acting_manager_id"))
    leave_request = _service.reject_leave_request(
        request_id,
        acting_manager_id,
        notes=payload.get("notes"),
        bypass_authorization=is_admin(),
    )
    return jsonify(data=_schema.dump(leave_request)), 200


@leave_bp.post("/<int:request_id>/cancel")
@login_required
def cancel_leave_request(request_id: int):
    payload = _cancel_schema.load(request.get_json(force=True, silent=True) or {})
    actor_employee_id = _resolve_acting_employee_id(payload.get("actor_employee_id"))
    leave_request = _service.cancel_leave_request(
        request_id, actor_employee_id, bypass_ownership=is_admin()
    )
    return jsonify(data=_schema.dump(leave_request)), 200
