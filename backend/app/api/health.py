from flask import Blueprint, jsonify
from sqlalchemy import text

from app.extensions import db

health_bp = Blueprint("health", __name__, url_prefix="/api")


@health_bp.get("/health")
def health():
    """Liveness/readiness probe used by Docker HEALTHCHECK and manual checks."""
    db_status = "ok"
    try:
        db.session.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 - deliberately broad for a health probe
        db_status = f"error: {exc}"

    return jsonify(status="ok", database=db_status), 200