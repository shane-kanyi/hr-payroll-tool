from marshmallow import Schema, fields, validate

from app.models import ALL_ROLES


class LoginSchema(Schema):
    email = fields.Email(required=True)
    password = fields.Str(required=True, validate=validate.Length(min=1))


class UserCreateSchema(Schema):
    email = fields.Email(required=True)
    password = fields.Str(required=True, validate=validate.Length(min=8, max=255))
    role = fields.Str(required=True, validate=validate.OneOf(ALL_ROLES))
    employee_id = fields.Int(required=False, allow_none=True, load_default=None)


class _EmployeeRefSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(dump_only=True)


class UserSchema(Schema):
    id = fields.Int(dump_only=True)
    email = fields.Str(dump_only=True)
    role = fields.Function(lambda obj: obj.role.name)
    employee = fields.Nested(_EmployeeRefSchema, dump_only=True, allow_none=True)
    is_active = fields.Bool(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
