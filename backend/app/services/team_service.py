from app.extensions import db
from app.models import Team
from app.repositories.team_repository import TeamRepository
from app.utils.errors import ConflictError, NotFoundError


class TeamService:
    def __init__(self, repo: TeamRepository | None = None):
        self.repo = repo or TeamRepository()

    def list_teams(self) -> list[Team]:
        return self.repo.list()

    def get_team(self, team_id: int) -> Team:
        team = self.repo.get_by_id(team_id)
        if team is None:
            raise NotFoundError(f"Team {team_id} not found")
        return team

    def create_team(self, name: str) -> Team:
        if self.repo.get_by_name(name):
            raise ConflictError(f"Team '{name}' already exists")
        team = Team(name=name)
        self.repo.add(team)
        db.session.commit()
        return team