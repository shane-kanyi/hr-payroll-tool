from app.extensions import db
from app.models.mixins import TimestampMixin


class Role(db.Model, TimestampMixin):
    __tablename__ = "roles"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

    users = db.relationship("User", back_populates="role")

    def __repr__(self) -> str:
        return f"<Role {self.name!r}>"