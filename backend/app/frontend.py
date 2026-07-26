import os

from flask import Flask, send_from_directory


def register_frontend(app: Flask) -> None:
    """Serves the vanilla-JS dashboard from the same process as the API.

    Local development and docker-compose keep using nginx as a separate
    container (see frontend/Dockerfile) - two processes with a clear
    separation of concerns. This exists for single-service hosting
    (e.g. a free-tier PaaS deploy) where running a second service just to
    serve static files isn't worth the extra moving part. It only
    activates if FRONTEND_DIST_DIR points at a real directory, so it's a
    no-op everywhere else, including every existing test.
    """
    frontend_dir = os.environ.get("FRONTEND_DIST_DIR", "/static_frontend")
    if not os.path.isdir(frontend_dir):
        return

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def serve_frontend(path):
        full_path = os.path.join(frontend_dir, path)
        if path and os.path.isfile(full_path):
            return send_from_directory(frontend_dir, path)
        return send_from_directory(frontend_dir, "index.html")
