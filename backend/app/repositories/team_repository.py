from app.extensions import db
from app.models import Team


class TeamRepository:
    def __init__(self, session=None):
        self.session = session or db.session

    def get_by_id(self, team_id: int) -> Team | None:
        return self.session.get(Team, team_id)

    def get_by_name(self, name: str) -> Team | None:
        return self.session.query(Team).filter(Team.name == name).first()

    def list(self) -> list[Team]:
        return self.session.query(Team).order_by(Team.name).all()

    def add(self, team: Team) -> Team:
        self.session.add(team)
        return team