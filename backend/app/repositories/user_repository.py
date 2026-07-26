from __future__ import annotations

from app.extensions import db
from app.models import User


class UserRepository:
    def __init__(self, session=None):
        self.session = session or db.session

    def get_by_id(self, user_id: int) -> User | None:
        return self.session.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        return self.session.query(User).filter(User.email == email.lower()).first()

    def get_by_employee_id(self, employee_id: int) -> User | None:
        return self.session.query(User).filter(User.employee_id == employee_id).first()

    def list(self) -> list[User]:
        return self.session.query(User).order_by(User.email).all()

    def add(self, user: User) -> User:
        self.session.add(user)
        return user
