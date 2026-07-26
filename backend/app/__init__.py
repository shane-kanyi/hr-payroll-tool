import logging
import os

from flask import Flask

from app.config import CONFIG_BY_NAME
from app.extensions import db, migrate, jwt, cors


def create_app(config_name: str | None = None) -> Flask:
    """Application factory.

    Keeping this as a factory (rather than a module-level `app`) is what
    lets pytest spin up isolated app instances per test with TestingConfig,
    and lets gunicorn/wsgi.py build the production instance the same way.
    """
    config_name = config_name or os.environ.get("FLASK_ENV", "development")

    app = Flask(__name__)
    app.config.from_object(CONFIG_BY_NAME[config_name])

    _configure_logging(app)

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}})

    from app import models

    _register_jwt_callbacks(app)

    from app.api.health import health_bp
    app.register_blueprint(health_bp)

    from app.api.auth import auth_bp
    app.register_blueprint(auth_bp)

    from app.api.teams import teams_bp
    app.register_blueprint(teams_bp)

    from app.api.employees import employees_bp
    app.register_blueprint(employees_bp)

    from app.api.leave import leave_bp
    app.register_blueprint(leave_bp)

    from app.api.payroll import payroll_bp
    app.register_blueprint(payroll_bp)

    from app.cli import register_cli_commands
    register_cli_commands(app)

    from app.seed import register_seed_command
    register_seed_command(app)

    _register_error_handlers(app)

    return app


def _register_jwt_callbacks(app: Flask) -> None:
    from flask import jsonify

    from app.extensions import db as _db
    from app.models import User

    @jwt.user_identity_loader
    def user_identity_lookup(user):
        return str(user.id) if isinstance(user, User) else str(user)

    @jwt.user_lookup_loader
    def user_lookup_callback(_jwt_header, jwt_data):
        # Re-fetches the User row on every request (rather than trusting
        # stale JWT claims) so a deactivated account loses access
        # immediately instead of only once its token happens to expire.
        return _db.session.get(User, int(jwt_data["sub"]))

    @jwt.unauthorized_loader
    def handle_missing_token(reason):
        return jsonify(message=f"Authentication required: {reason}"), 401

    @jwt.invalid_token_loader
    def handle_invalid_token(reason):
        return jsonify(message=f"Invalid authentication token: {reason}"), 401

    @jwt.expired_token_loader
    def handle_expired_token(_jwt_header, _jwt_payload):
        return jsonify(message="Authentication token has expired"), 401


def _register_error_handlers(app: Flask) -> None:
    from flask import jsonify
    from marshmallow import ValidationError as MarshmallowValidationError
    from app.utils.errors import AppError

    @app.errorhandler(AppError)
    def handle_app_error(err: AppError):
        return jsonify(err.to_dict()), err.status_code

    @app.errorhandler(MarshmallowValidationError)
    def handle_marshmallow_error(err: MarshmallowValidationError):
        return jsonify(message="Validation failed", errors=err.messages), 400

    @app.errorhandler(404)
    def handle_404(err):
        return jsonify(message="Resource not found"), 404

    @app.errorhandler(500)
    def handle_500(err):
        app.logger.exception("Unhandled server error")
        return jsonify(message="Internal server error"), 500


    return app


def _configure_logging(app: Flask) -> None:
    level = logging.DEBUG if app.debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    app.logger.setLevel(level)