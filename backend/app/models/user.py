from app.extensions import db
from app.models.mixins import TimestampMixin


class User(db.Model, TimestampMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    employee_id = db.Column(
        db.Integer, db.ForeignKey("employees.id"), nullable=True, unique=True
    )
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)

    is_active = db.Column(db.Boolean, nullable=False, default=True)

    employee = db.relationship("Employee")
    role = db.relationship("Role", back_populates="users")

    def __repr__(self) -> str:
        return f"<User {self.id} {self.email!r}>"