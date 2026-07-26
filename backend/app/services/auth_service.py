from __future__ import annotations

from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from app.models import ALL_ROLES, User
from app.repositories.employee_repository import EmployeeRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository
from app.utils.errors import ConflictError, NotFoundError, UnauthorizedError, ValidationError


class AuthService:
    def __init__(
        self,
        user_repo: UserRepository | None = None,
        role_repo: RoleRepository | None = None,
        employee_repo: EmployeeRepository | None = None,
    ):
        self.user_repo = user_repo or UserRepository()
        self.role_repo = role_repo or RoleRepository()
        self.employee_repo = employee_repo or EmployeeRepository()

    # ---- authentication -----------------------------------------------

    def authenticate(self, email: str, password: str) -> User:
        user = self.user_repo.get_by_email(email)
        if user is None or not check_password_hash(user.password_hash, password):
            # Deliberately identical message/status for "no such user" and
            # "wrong password" - distinguishing them lets an attacker
            # enumerate valid emails.
            raise UnauthorizedError("Invalid email or password")
        if not user.is_active:
            raise UnauthorizedError("This account has been deactivated")
        return user

    # ---- reads -----------------------------------------------------------

    def get_user(self, user_id: int) -> User:
        user = self.user_repo.get_by_id(user_id)
        if user is None:
            raise NotFoundError(f"User {user_id} not found")
        return user

    def list_users(self) -> list[User]:
        return self.user_repo.list()

    # ---- writes ------------------------------------------------------------

    def create_user(self, data: dict) -> User:
        email = data["email"].strip().lower()
        if self.user_repo.get_by_email(email) is not None:
            raise ConflictError(f"A user with email {email} already exists")

        role_name = data["role"]
        if role_name not in ALL_ROLES:
            raise ValidationError(f"role must be one of {ALL_ROLES}")

        employee_id = data.get("employee_id")
        if employee_id is not None:
            if self.employee_repo.get_by_id(employee_id) is None:
                raise ValidationError(f"Employee {employee_id} does not exist")
            if self.user_repo.get_by_employee_id(employee_id) is not None:
                raise ConflictError(f"Employee {employee_id} already has a linked user account")

        role = self.role_repo.get_or_create(role_name)
        user = User(
            email=email,
            password_hash=generate_password_hash(data["password"]),
            role=role,
            employee_id=employee_id,
            is_active=True,
        )
        self.user_repo.add(user)
        db.session.commit()
        return user

    def deactivate_user(self, user_id: int) -> User:
        user = self.get_user(user_id)
        if not user.is_active:
            raise ConflictError(f"User {user_id} is already inactive")
        user.is_active = False
        db.session.commit()
        return user

    def reactivate_user(self, user_id: int) -> User:
        user = self.get_user(user_id)
        if user.is_active:
            raise ConflictError(f"User {user_id} is already active")
        user.is_active = True
        db.session.commit()
        return user
