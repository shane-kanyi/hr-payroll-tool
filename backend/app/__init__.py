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

    from app.api.health import health_bp
    app.register_blueprint(health_bp)

    # Feature blueprints (employees, leave, payroll, auth, dashboard) are
    # registered here in later phases as they're built, e.g.:
    #   from app.api.employees import employees_bp
    #   app.register_blueprint(employees_bp)

    return app


def _configure_logging(app: Flask) -> None:
    level = logging.DEBUG if app.debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    app.logger.setLevel(level)