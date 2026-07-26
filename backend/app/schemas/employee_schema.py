from marshmallow import Schema, fields, validate

from app.models import EmploymentType

_EMPLOYMENT_TYPE_VALUES = [e.value for e in EmploymentType]


class TeamRefSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(dump_only=True)


class ManagerRefSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(dump_only=True)


class EmployeeCreateSchema(Schema):
    name = fields.Str(required=True, validate=validate.Length(min=1, max=150))
    role = fields.Str(required=True, validate=validate.Length(min=1, max=120))
    team_id = fields.Int(required=False, allow_none=True, load_default=None)
    manager_id = fields.Int(required=False, allow_none=True, load_default=None)
    start_date = fields.Date(required=True)
    salary = fields.Decimal(
        required=True, as_string=True, places=2, validate=validate.Range(min=0)
    )
    employment_type = fields.Str(
        required=True, validate=validate.OneOf(_EMPLOYMENT_TYPE_VALUES)
    )


class EmployeeUpdateSchema(Schema):
    name = fields.Str(validate=validate.Length(min=1, max=150))
    role = fields.Str(validate=validate.Length(min=1, max=120))
    team_id = fields.Int(allow_none=True)
    manager_id = fields.Int(allow_none=True)
    start_date = fields.Date()
    salary = fields.Decimal(as_string=True, places=2, validate=validate.Range(min=0))
    employment_type = fields.Str(validate=validate.OneOf(_EMPLOYMENT_TYPE_VALUES))


class EmployeeSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str()
    role = fields.Str()
    team = fields.Nested(TeamRefSchema, dump_only=True, allow_none=True)
    manager = fields.Nested(ManagerRefSchema, dump_only=True, allow_none=True)
    start_date = fields.Date()
    salary = fields.Decimal(as_string=True, places=2)
    employment_type = fields.Function(lambda obj: obj.employment_type.value)
    is_active = fields.Bool(dump_only=True)
    deactivated_at = fields.DateTime(dump_only=True, allow_none=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


class EmployeeListQuerySchema(Schema):
    """Validates query-string filters for GET /api/employees."""

    is_active = fields.Bool(required=False)
    team_id = fields.Int(required=False)
    manager_id = fields.Int(required=False)
    search = fields.Str(required=False, validate=validate.Length(max=150))
    page = fields.Int(required=False, load_default=1, validate=validate.Range(min=1))
    per_page = fields.Int(
        required=False, load_default=20, validate=validate.Range(min=1, max=100)
    )