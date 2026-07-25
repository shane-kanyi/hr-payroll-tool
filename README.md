# HR & Payroll Tool

A lightweight internal app for managing employee records, leave requests,
and monthly payroll. The goal is to replace spreadsheet + WhatsApp approvals
with a small system that captures real business logic.

## Overview

- Backend: Flask with application factory and blueprints
- ORM: SQLAlchemy + Flask-Migrate / Alembic
- Database: PostgreSQL
- Frontend: plain HTML / CSS / vanilla JavaScript (no build step)
- Testing: pytest
- Containers: Docker + docker-compose

## Status

This repository is currently scaffolded. It includes:

- Flask app factory structure
- Docker + PostgreSQL wiring
- `/api/health` endpoint that verifies both the application and DB connectivity

Domain logic for employees, leave, and payroll is not implemented yet.

## Requirements

- Python 3.x
- PostgreSQL (for local development and tests)
- Docker and docker-compose (for containerized setup)

## Quick start (Docker)

```bash
cp backend/.env.example backend/.env
docker compose up --build
```

- API: `http://localhost:5000/api/health`
- Frontend: `http://localhost:8080`

## Quick start (local, no Docker)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
flask run
```

## Running tests

```bash
cd backend
source .venv/bin/activate
pytest
```

> Tests are configured to run against a real PostgreSQL database rather than
> SQLite. This avoids false-positive results for Postgres-specific behavior,
> such as range overlap queries for leave detection.

## Project layout

```text
hr-payroll-tool/
├── backend/
│   ├── app/
│   │   ├── api/           # Flask blueprints (health.py so far)
│   │   ├── models/        # empty, added when the schema is built
│   │   ├── repositories/  # empty
│   │   ├── services/      # empty
│   │   ├── schemas/       # empty
│   │   ├── utils/         # empty
│   │   ├── init.py        # create_app() factory
│   │   ├── config.py
│   │   └── extensions.py
│   ├── migrations/        # empty, Alembic init pending
│   ├── tests/
│   ├── wsgi.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── css/
│   ├── js/
│   ├── index.html
│   └── Dockerfile
├── docker-compose.yml
└── README.md
```

## Architecture notes

- **Service layer between API and DB**: keep blueprints thin with request
  parsing, service invocation, and response serialization.
- **Repository layer**: encapsulate SQLAlchemy queries so services do not
  build database queries inline.
- **App factory**: enable isolated testing with a `TestingConfig` instance
  instead of using dev/prod configuration.
- **Frontend without build tooling**: serve plain HTML/CSS/JS through nginx
  and proxy API calls to the Flask backend at `/api/*`.

## Notes

- The health check executes `SELECT 1` against PostgreSQL, so the endpoint
  verifies actual DB reachability instead of only Flask availability.
- PostgreSQL is used for tests from the start to avoid a false-green suite
  once leave overlap logic is implemented.
