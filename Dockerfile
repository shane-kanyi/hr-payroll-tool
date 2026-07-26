# Single-service build for free-tier PaaS hosting (Render, etc.): the
# Flask API and the static dashboard are served from one process on one
# port, so only one web service + one Postgres instance need to exist.
#
# Local development keeps using docker-compose (backend/Dockerfile +
# frontend/Dockerfile as two containers behind nginx) - this file is not
# part of that setup and does not replace it. See docs/HOSTING.md.

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt backend/requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./
RUN chmod +x docker-entrypoint.sh

COPY frontend/ /static_frontend/
ENV FRONTEND_DIST_DIR=/static_frontend

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT:-5000}/api/health || exit 1

ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-5000} --workers 2 wsgi:app"]
