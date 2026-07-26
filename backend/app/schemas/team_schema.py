from marshmallow import Schema, fields, validate


class TeamCreateSchema(Schema):
    name = fields.Str(required=True, validate=validate.Length(min=1, max=120))


class TeamSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str()
    created_at = fields.DateTime(dump_only=True)