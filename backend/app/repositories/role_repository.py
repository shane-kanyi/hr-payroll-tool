from __future__ import annotations

from app.extensions import db
from app.models import Role


class RoleRepository:
    def __init__(self, session=None):
        self.session = session or db.session

    def get_by_name(self, name: str) -> Role | None:
        return self.session.query(Role).filter(Role.name == name).first()

    def get_or_create(self, name: str) -> Role:
        role = self.get_by_name(name)
        if role is not None:
            return role
        role = Role(name=name)
        self.session.add(role)
        self.session.flush()
        return role

    def list(self) -> list[Role]:
        return self.session.query(Role).order_by(Role.name).all()
