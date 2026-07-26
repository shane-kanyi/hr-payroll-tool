from app.extensions import db
from app.models.mixins import TimestampMixin


class Team(db.Model, TimestampMixin):
    __tablename__ = "teams"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)

    employees = db.relationship(
        "Employee", back_populates="team", foreign_keys="Employee.team_id"
    )

    def __repr__(self) -> str:
        return f"<Team {self.id} {self.name!r}>"