from marshmallow import Schema, fields, validate

from app.models import PayrollPeriodStatus

_PERIOD_STATUS_VALUES = [s.value for s in PayrollPeriodStatus]


class _EmployeeRefSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(dump_only=True)


class PayrollGenerateSchema(Schema):
    year = fields.Int(required=True, validate=validate.Range(min=2000, max=2100))
    month = fields.Int(required=True, validate=validate.Range(min=1, max=12))
    # generated_by_id is not client-supplied - it's always the logged-in
    # Admin's linked employee id (may be None), set in app/api/payroll.py.


class PayrollPeriodListQuerySchema(Schema):
    page = fields.Int(required=False, load_default=1, validate=validate.Range(min=1))
    per_page = fields.Int(
        required=False, load_default=20, validate=validate.Range(min=1, max=100)
    )


class PayrollEntryListQuerySchema(Schema):
    employee_id = fields.Int(required=False)


class PayrollPeriodSchema(Schema):
    id = fields.Int(dump_only=True)
    year = fields.Int(dump_only=True)
    month = fields.Int(dump_only=True)
    status = fields.Function(lambda obj: obj.status.value)
    generated_at = fields.DateTime(dump_only=True, allow_none=True)
    generated_by = fields.Nested(_EmployeeRefSchema, dump_only=True, allow_none=True)
    finalized_at = fields.DateTime(dump_only=True, allow_none=True)
    entry_count = fields.Function(lambda obj: len(obj.entries))
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


class PayrollEntrySchema(Schema):
    id = fields.Int(dump_only=True)
    payroll_period_id = fields.Int(dump_only=True)
    employee = fields.Nested(_EmployeeRefSchema, dump_only=True)
    gross_salary = fields.Decimal(as_string=True, places=2, dump_only=True)
    unpaid_leave_days = fields.Decimal(as_string=True, places=2, dump_only=True)
    unpaid_leave_deduction = fields.Decimal(as_string=True, places=2, dump_only=True)
    taxable_income = fields.Decimal(as_string=True, places=2, dump_only=True)
    tax_deduction = fields.Decimal(as_string=True, places=2, dump_only=True)
    social_security_deduction = fields.Decimal(as_string=True, places=2, dump_only=True)
    net_salary = fields.Decimal(as_string=True, places=2, dump_only=True)
    calculation_notes = fields.Raw(dump_only=True)
