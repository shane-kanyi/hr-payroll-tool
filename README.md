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

Employee management is functional end-to-end: teams and employees CRUD,
soft-delete (deactivate/reactivate), org hierarchy view, and two real
business-rule safeguards (circular reporting chains, deactivating a
manager who still has active reports).

Leave management is also functional end-to-end: submit/approve/reject/
cancel, overlap detection, prorated balance provisioning and validation,
minimum notice period, team-coverage safeguard on approval, and a
pending-vs-escalated (skip-level manager) resolution path.

Payroll is functional end-to-end: generate a monthly run (draft, freely
recomputable), finalize it (permanently locked, snapshotted), per-employee
payslips with a full calculation breakdown, and a progressive tax + flat
social-security scheme. Mid-month joiners/exits are prorated, unpaid leave
(pulled directly from the leave engine) reduces taxable income, and salary
near a tax-bracket boundary is handled correctly by marginal (not flat-rate)
tax brackets. 145 tests passing, 97% coverage on `app/`. Dashboard UI is
next — no frontend yet beyond the scaffold.

See `docs/ERD.md` for the schema, `docs/API.md` for endpoint details,
`docs/LEAVE.md` for the leave business rules, and `docs/PAYROLL.md` for the
payroll formula and assumptions.

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
│   │   ├── api/              # health, teams, employees, leave, payroll blueprints
│   │   ├── models/           # team, employee, role, user, leave, payroll, audit_log
│   │   ├── repositories/     # team, employee, leave_request, leave_balance, payroll_period, payroll_entry
│   │   ├── services/         # team, employee, leave, payroll services (business rules)
│   │   ├── schemas/          # team, employee, leave, payroll (marshmallow)
│   │   ├── utils/            # errors.py, dates.py (business-day math), tax.py (progressive brackets)
│   │   ├── __init__.py       # create_app() factory + error handlers
│   │   ├── config.py
│   │   └── extensions.py
│   ├── migrations/
│   │   └── versions/
│   ├── tests/
│   │   ├── test_health.py
│   │   ├── test_models.py
│   │   ├── test_employee_service.py
│   │   ├── test_employees_api.py
│   │   ├── test_leave_service.py
│   │   ├── test_leave_api.py
│   │   ├── test_tax.py
│   │   ├── test_payroll_service.py
│   │   └── test_payroll_api.py
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
- `flask db init` refuses to run if `migrations/` already has anything in
  it — even just a `.gitkeep`. Hit this after cloning fresh; fix is
  `rm -f migrations/.gitkeep` (or `rm -rf migrations/` if it's not empty
  for some other reason) before re-running `flask db init`.
- **Circular manager chains**: nothing in a spreadsheet stops someone
  setting Alice's manager to Bob and Bob's manager to Alice on two
  different rows. `EmployeeService._validate_manager` walks the proposed
  manager's chain upward on every create/update and rejects the change if
  it would ever loop back to the employee being edited. Self-management
  (`manager_id == employee_id`) is rejected as a special case of the same
  check.
- **Deactivating a manager**: refused if they still have active direct
  reports, rather than silently leaving those reports pointing at a
  now-inactive manager. The 409 response includes which reports are
  blocking it (`blocking_reports: [id, ...]`) so the frontend can link
  straight to them instead of just saying "no."
- `is_active` is deliberately excluded from the employee update schema —
  status changes only happen through `/deactivate` and `/reactivate`, so
  there's one auditable code path per state transition instead of a
  generic PUT quietly flipping it. marshmallow's default `unknown=RAISE`
  enforces this for free: sending `is_active` in a PUT body fails the
  whole request with 400 rather than being silently ignored.
- Hit a real bug from naming a repository method `list()` — it shadowed
  the builtin `list` for every `list[SomeType]` type hint written *later*
  in the same class body, crashing at import time with `'function' object
  is not subscriptable`. Fixed with `from __future__ import annotations`
  at the top of that file.
- **Leave engine (Phase 3)**: full rules and assumptions are in
  `docs/LEAVE.md` — overlap detection (checked again at approval time, not
  just submission, to catch the race where a second pending request only
  starts conflicting once the first one is approved), prorated balance
  provisioning, minimum notice period, a team-coverage safeguard on
  approval, and escalation of stale pending requests to a skip-level
  manager. Auth doesn't exist yet, so `acting_manager_id` /
  `actor_employee_id` are passed explicitly in request bodies as a
  documented interim stand-in for real caller identity — Phase 6 will
  remove them in favor of JWT-derived identity.
- No scheduler exists yet for the escalation sweep; it's exposed as
  `POST /api/leave-requests/escalate` for now (manual or external-cron
  trigger) rather than adding a background-job dependency a phase early.
- **Payroll engine (Phase 4)**: full formula and edge cases are in
  `docs/PAYROLL.md`. The two day-count bases are deliberately different —
  mid-month join/exit proration uses calendar days (a flat salary "covers"
  every day of the month), while unpaid-leave deduction uses working days
  (leave only costs you a day you'd otherwise have worked) — worth reading
  before it looks like a bug. Tax is marginal/progressive specifically so a
  salary one dollar over a bracket boundary is never worse off than one
  dollar under it; `test_no_cliff_at_bracket_boundary` in `test_tax.py`
  demonstrates this directly. Needed zero new migrations — the Phase 1
  `payroll_entries` columns already matched the calculation pipeline.
