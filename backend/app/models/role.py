from app.extensions import db
from app.models.mixins import TimestampMixin

ROLE_ADMIN = "admin"
ROLE_MANAGER = "manager"
ROLE_EMPLOYEE = "employee"
ALL_ROLES = (ROLE_ADMIN, ROLE_MANAGER, ROLE_EMPLOYEE)


class Role(db.Model, TimestampMixin):
    __tablename__ = "roles"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

    users = db.relationship("User", back_populates="role")

    __table_args__ = (
        db.CheckConstraint(f"name IN {ALL_ROLES}", name="ck_roles_name_valid"),
    )

    def __repr__(self) -> str:
        return f"<Role {self.name!r}>"
