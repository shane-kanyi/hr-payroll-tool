from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token

from app.models import ROLE_ADMIN
from app.schemas.auth_schema import LoginSchema, UserCreateSchema, UserSchema
from app.services.auth_service import AuthService
from app.utils.auth import current_user, login_required, roles_required

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

_service = AuthService()
_login_schema = LoginSchema()
_user_create_schema = UserCreateSchema()
_user_schema = UserSchema()
_user_list_schema = UserSchema(many=True)


@auth_bp.post("/login")
def login():
    payload = _login_schema.load(request.get_json(force=True, silent=True) or {})
    user = _service.authenticate(payload["email"], payload["password"])
    token = create_access_token(identity=user)
    return (
        jsonify(data={"access_token": token, "user": _user_schema.dump(user)}),
        200,
    )


@auth_bp.get("/me")
@login_required
def me():
    return jsonify(data=_user_schema.dump(current_user())), 200


@auth_bp.get("/users")
@roles_required(ROLE_ADMIN)
def list_users():
    users = _service.list_users()
    return jsonify(data=_user_list_schema.dump(users)), 200


@auth_bp.post("/users")
@roles_required(ROLE_ADMIN)
def create_user():
    payload = _user_create_schema.load(request.get_json(force=True, silent=True) or {})
    user = _service.create_user(payload)
    return jsonify(data=_user_schema.dump(user)), 201


@auth_bp.post("/users/<int:user_id>/deactivate")
@roles_required(ROLE_ADMIN)
def deactivate_user(user_id: int):
    user = _service.deactivate_user(user_id)
    return jsonify(data=_user_schema.dump(user)), 200


@auth_bp.post("/users/<int:user_id>/reactivate")
@roles_required(ROLE_ADMIN)
def reactivate_user(user_id: int):
    user = _service.reactivate_user(user_id)
    return jsonify(data=_user_schema.dump(user)), 200
