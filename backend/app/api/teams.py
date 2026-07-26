from flask import Blueprint, jsonify, request

from app.schemas.team_schema import TeamCreateSchema, TeamSchema
from app.services.team_service import TeamService

teams_bp = Blueprint("teams", __name__, url_prefix="/api/teams")

_service = TeamService()
_create_schema = TeamCreateSchema()
_schema = TeamSchema()
_list_schema = TeamSchema(many=True)


@teams_bp.get("")
def list_teams():
    teams = _service.list_teams()
    return jsonify(data=_list_schema.dump(teams)), 200


@teams_bp.post("")
def create_team():
    payload = _create_schema.load(request.get_json(force=True, silent=True) or {})
    team = _service.create_team(payload["name"])
    return jsonify(data=_schema.dump(team)), 201


@teams_bp.get("/<int:team_id>")
def get_team(team_id: int):
    team = _service.get_team(team_id)
    return jsonify(data=_schema.dump(team)), 200