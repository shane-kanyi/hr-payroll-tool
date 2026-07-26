from datetime import date

from flask import Blueprint, jsonify, request

from app.schemas.leave_schema import (
    LeaveBalanceSchema,
    LeaveCancelSchema,
    LeaveDecisionSchema,
    LeaveRequestCreateSchema,
    LeaveRequestListQuerySchema,
    LeaveRequestSchema,
)
from app.services.leave_service import LeaveService
from app.utils.errors import ValidationError

leave_bp = Blueprint("leave_requests", __name__, url_prefix="/api/leave-requests")

_service = LeaveService()
_create_schema = LeaveRequestCreateSchema()
_decision_schema = LeaveDecisionSchema()
_cancel_schema = LeaveCancelSchema()
_query_schema = LeaveRequestListQuerySchema()
_schema = LeaveRequestSchema()
_list_schema = LeaveRequestSchema(many=True)
_balance_list_schema = LeaveBalanceSchema(many=True)


@leave_bp.get("")
def list_leave_requests():
    filters = _query_schema.load(request.args.to_dict())
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
def pending_approvals():
    manager_id = request.args.get("manager_id", type=int)
    if manager_id is None:
        raise ValidationError("manager_id query parameter is required")
    items = _service.list_pending_approvals_for_manager(manager_id)
    return jsonify(data=_list_schema.dump(items)), 200


@leave_bp.get("/on-leave")
def on_leave():
    raw_date = request.args.get("date")
    on_date = date.fromisoformat(raw_date) if raw_date else None
    items = _service.who_is_on_leave(on_date)
    return jsonify(data=_list_schema.dump(items)), 200


@leave_bp.get("/balances")
def leave_balances():
    employee_id = request.args.get("employee_id", type=int)
    if employee_id is None:
        raise ValidationError("employee_id query parameter is required")
    year = request.args.get("year", type=int)
    balances = _service.get_leave_balances(employee_id, year=year)
    return jsonify(data=_balance_list_schema.dump(balances)), 200


@leave_bp.post("/escalate")
def run_escalation_sweep():
    escalated = _service.run_escalation_sweep()
    return jsonify(data=_list_schema.dump(escalated), meta={"escalated_count": len(escalated)}), 200


@leave_bp.get("/<int:request_id>")
def get_leave_request(request_id: int):
    leave_request = _service.get_leave_request(request_id)
    return jsonify(data=_schema.dump(leave_request)), 200


@leave_bp.post("")
def submit_leave_request():
    payload = _create_schema.load(request.get_json(force=True, silent=True) or {})
    leave_request = _service.submit_leave_request(payload)
    return jsonify(data=_schema.dump(leave_request)), 201


@leave_bp.post("/<int:request_id>/approve")
def approve_leave_request(request_id: int):
    payload = _decision_schema.load(request.get_json(force=True, silent=True) or {})
    leave_request = _service.approve_leave_request(
        request_id, payload["acting_manager_id"], notes=payload.get("notes")
    )
    return jsonify(data=_schema.dump(leave_request)), 200


@leave_bp.post("/<int:request_id>/reject")
def reject_leave_request(request_id: int):
    payload = _decision_schema.load(request.get_json(force=True, silent=True) or {})
    leave_request = _service.reject_leave_request(
        request_id, payload["acting_manager_id"], notes=payload.get("notes")
    )
    return jsonify(data=_schema.dump(leave_request)), 200


@leave_bp.post("/<int:request_id>/cancel")
def cancel_leave_request(request_id: int):
    payload = _cancel_schema.load(request.get_json(force=True, silent=True) or {})
    leave_request = _service.cancel_leave_request(request_id, payload["actor_employee_id"])
    return jsonify(data=_schema.dump(leave_request)), 200
