from marshmallow import Schema, fields, validate

from app.models import LeaveStatus, LeaveType

_LEAVE_TYPE_VALUES = [t.value for t in LeaveType]
_LEAVE_STATUS_VALUES = [s.value for s in LeaveStatus]


class _EmployeeRefSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(dump_only=True)


class LeaveRequestCreateSchema(Schema):
    # employee_id is optional: it's derived from the logged-in user by
    # default and only honored as an explicit override for Admins (e.g. HR
    # entering leave on someone's behalf). See app/api/leave.py.
    employee_id = fields.Int(required=False, allow_none=True, load_default=None)
    leave_type = fields.Str(required=True, validate=validate.OneOf(_LEAVE_TYPE_VALUES))
    start_date = fields.Date(required=True)
    end_date = fields.Date(required=True)
    reason = fields.Str(required=False, allow_none=True, validate=validate.Length(max=2000))


class LeaveDecisionSchema(Schema):
    # acting_manager_id is likewise Admin-override-only; a Manager always
    # acts as themselves, derived from their logged-in identity.
    acting_manager_id = fields.Int(required=False, allow_none=True, load_default=None)
    notes = fields.Str(required=False, allow_none=True, validate=validate.Length(max=2000))


class LeaveCancelSchema(Schema):
    actor_employee_id = fields.Int(required=False, allow_none=True, load_default=None)


class LeaveRequestSchema(Schema):
    id = fields.Int(dump_only=True)
    employee = fields.Nested(_EmployeeRefSchema, dump_only=True)
    leave_type = fields.Function(lambda obj: obj.leave_type.value)
    start_date = fields.Date(dump_only=True)
    end_date = fields.Date(dump_only=True)
    days_requested = fields.Decimal(as_string=True, places=2, dump_only=True)
    status = fields.Function(lambda obj: obj.status.value)
    reason = fields.Str(dump_only=True, allow_none=True)
    requested_at = fields.DateTime(dump_only=True)
    decided_by = fields.Nested(_EmployeeRefSchema, dump_only=True, allow_none=True)
    decided_at = fields.DateTime(dump_only=True, allow_none=True)
    decision_notes = fields.Str(dump_only=True, allow_none=True)
    escalated_at = fields.DateTime(dump_only=True, allow_none=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


class LeaveRequestListQuerySchema(Schema):
    employee_id = fields.Int(required=False)
    manager_id = fields.Int(required=False)
    status = fields.Str(required=False, validate=validate.OneOf(_LEAVE_STATUS_VALUES))
    escalated_only = fields.Bool(required=False, load_default=False)
    page = fields.Int(required=False, load_default=1, validate=validate.Range(min=1))
    per_page = fields.Int(
        required=False, load_default=20, validate=validate.Range(min=1, max=100)
    )


class LeaveBalanceQuerySchema(Schema):
    year = fields.Int(required=False)


class LeaveBalanceSchema(Schema):
    id = fields.Int(dump_only=True)
    employee_id = fields.Int(dump_only=True)
    leave_type = fields.Function(lambda obj: obj.leave_type.value)
    year = fields.Int(dump_only=True)
    allocated_days = fields.Decimal(as_string=True, places=2, dump_only=True)
    used_days = fields.Decimal(as_string=True, places=2, dump_only=True)
    remaining_days = fields.Decimal(as_string=True, places=2, dump_only=True)
