from __future__ import annotations

from functools import wraps

from flask_jwt_extended import current_user as jwt_current_user
from flask_jwt_extended import verify_jwt_in_request

from app.models import ROLE_ADMIN
from app.utils.errors import ForbiddenError


def _ensure_active() -> None:
    if jwt_current_user is None or not jwt_current_user.is_active:
        raise ForbiddenError("Your account has been deactivated")


def login_required(fn):
    """Any authenticated, active user - no role restriction."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        _ensure_active()
        return fn(*args, **kwargs)

    return wrapper


def roles_required(*roles: str):
    """Authenticated, active user whose role is one of `roles`."""

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            _ensure_active()
            if jwt_current_user.role.name not in roles:
                raise ForbiddenError(
                    f"This action requires one of the following roles: {', '.join(roles)}"
                )
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def current_user():
    """The live User row for the current request, or None if unauthenticated.

    Populated per-request by the user_lookup_loader in app/__init__.py -
    always a fresh DB read, not just JWT claims, so a deactivated account
    loses access immediately rather than only once its token expires.
    """
    return jwt_current_user


def is_admin() -> bool:
    user = jwt_current_user
    return user is not None and user.role.name == ROLE_ADMIN
