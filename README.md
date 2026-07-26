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

All three core modules — employee records, leave management, and payroll —
plus authentication/RBAC and a working dashboard are complete and tested
end-to-end, backed by a Flask app factory, Docker + PostgreSQL wiring, and
an `/api/health` endpoint that verifies both the application and DB
connectivity.

**Employee management**: teams and employees CRUD, soft-delete
(deactivate/reactivate), org hierarchy view, and two real business-rule
safeguards (circular reporting chains, deactivating a manager who still
has active reports).

**Leave management**: submit/approve/reject/cancel, overlap detection,
prorated balance provisioning and validation, minimum notice period,
team-coverage safeguard on approval, and a pending-vs-escalated
(skip-level manager) resolution path.

**Payroll**: generate a monthly run (draft, freely recomputable), finalize
it (permanently locked, snapshotted), per-employee payslips with a full
calculation breakdown, and a progressive tax + flat social-security
scheme. Mid-month joiners/exits are prorated, unpaid leave (pulled
directly from the leave engine) reduces taxable income, and salary near a
tax-bracket boundary is handled correctly by marginal (not flat-rate) tax
brackets.

**Dashboard**: plain HTML/CSS/vanilla JS, no build step, no framework — an
Overview tab (pending approvals, who's out today, leave balances, recent
payroll runs), an Employees tab (create/search/filter/deactivate/
reactivate, org chart), a Leave tab (submit/approve/reject/cancel,
balances, who's-out, manual escalation trigger), and a Payroll tab
(generate/recompute/finalize, a per-employee entries table with an
expandable tax-bracket breakdown per payslip).

**Authentication & RBAC**: JWT login, three roles (Admin/Manager/Employee)
with a documented permission matrix, and identity (which employee is
submitting/approving/cancelling) always derived from the logged-in user
rather than trusted from the request body — Admins may still override it
explicitly, e.g. to act on behalf of someone. The frontend gates behind a
real login screen; the "Acting as" employee selector survives only as an
Admin-only override inside the Leave tab.

201 tests passing, 96% coverage on `app/`.

See `docs/ERD.md` for the schema, `docs/API.md` for endpoint details,
`docs/LEAVE.md` for the leave business rules, `docs/PAYROLL.md` for the
payroll formula, `docs/AUTH.md` for the RBAC matrix and identity model,
`docs/DEPLOYMENT.md` for environment variables and a pre-production
checklist, and `docs/HOSTING.md` for putting a live instance up on a free
hosting tier.

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
- Migrations and an admin account are applied/created automatically on
  startup (`backend/docker-entrypoint.sh`). Log in with the
  `ADMIN_EMAIL`/`ADMIN_PASSWORD` from `backend/.env` (defaults:
  `admin@example.com` / `ChangeMe123!` — **change this before deploying
  anywhere real**, see docs/AUTH.md).
- Want sample data (teams, employees, leave requests, a finalized payroll
  period) instead of an empty database? `docker compose exec backend flask
  seed-demo` — or restore `database/dump.sql` directly (see
  `database/README.md`).

## Quick start (local, no Docker)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
flask db upgrade
flask create-admin --email admin@example.com --password "ChangeMe123!"
flask seed-demo   # optional: sample teams/employees/leave/payroll data
flask run
```

Full environment variable reference and a pre-production checklist:
`docs/DEPLOYMENT.md`.

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
│   │   ├── api/              # health, auth, teams, employees, leave, payroll blueprints
│   │   ├── models/           # team, employee, role, user, leave, payroll, audit_log
│   │   ├── repositories/     # team, employee, leave_request, leave_balance, payroll_period,
│   │   │                     # payroll_entry, user, role
│   │   ├── services/         # team, employee, leave, payroll, auth services (business rules)
│   │   ├── schemas/          # team, employee, leave, payroll, auth (marshmallow)
│   │   ├── utils/            # errors.py, dates.py, tax.py, auth.py (RBAC decorators)
│   │   ├── cli.py            # `flask create-admin` bootstrap command
│   │   ├── seed.py           # `flask seed-demo` sample-data generator
│   │   ├── __init__.py       # create_app() factory + error/JWT handlers
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
│   │   ├── test_payroll_api.py
│   │   ├── test_auth_service.py
│   │   ├── test_auth_api.py
│   │   └── test_seed.py
│   ├── docker-entrypoint.sh  # migrate, then bootstrap admin, then exec gunicorn
│   ├── wsgi.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── css/theme.css     # design tokens, cards, tables, badges, forms, empty/loading states, login screen
│   ├── js/
│   │   ├── api.js        # fetch wrapper + namespaced endpoint helpers + 401 hook
│   │   ├── store.js      # currentUser, Admin-only "acting as" override, employee cache, pub/sub
│   │   ├── dom.js        # escapeHtml, loading/empty/error state renderers
│   │   ├── format.js     # money/date/badge formatting
│   │   ├── employees.js  # Employees tab: CRUD (Admin-gated), org chart
│   │   ├── leave.js      # Leave tab: submit/approve/reject/cancel, balances, who's-out
│   │   ├── payroll.js    # Payroll tab: Admin full view, self-service payslips otherwise
│   │   ├── dashboard.js  # Overview tab: role-aware summary of the above
│   │   └── main.js       # login/session bootstrap, tab routing, logout
│   ├── index.html
│   └── Dockerfile
├── database/
│   ├── dump.sql          # schema + sample data (see database/README.md)
│   └── README.md
├── docker-compose.yml
└── README.md
```

## Architecture notes

- **Service layer between API and DB**: keep blueprints thin with request
  parsing, service invocation, and response serialization. Services never
  touch HTTP concerns (auth, JWTs, roles) — they take plain parameters
  like an employee id, so they can be exercised directly in tests and
  reused unchanged as the API around them evolved.
- **Repository layer**: encapsulate SQLAlchemy queries so services do not
  build database queries inline.
- **App factory**: enable isolated testing with a `TestingConfig` instance
  instead of using dev/prod configuration.
- **Frontend without build tooling**: serve plain HTML/CSS/JS through nginx
  and proxy API calls to the Flask backend at `/api/*`.

## Notes

### Health & testing setup

- The health check executes `SELECT 1` against PostgreSQL, so the endpoint
  verifies actual DB reachability instead of only Flask availability.
- PostgreSQL is used for tests from the start to avoid a false-green suite
  once leave overlap logic is implemented.
- `flask db init` refuses to run if `migrations/` already has anything in
  it — even just a `.gitkeep`. Hit this after cloning fresh; fix is
  `rm -f migrations/.gitkeep` (or `rm -rf migrations/` if it's not empty
  for some other reason) before re-running `flask db init`.

### Employee lifecycle

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

### Leave engine

Full rules and assumptions are in `docs/LEAVE.md` — overlap detection
(checked again at approval time, not just submission, to catch the race
where a second pending request only starts conflicting once the first one
is approved), prorated balance provisioning, minimum notice period, a
team-coverage safeguard on approval, and escalation of stale pending
requests to a skip-level manager. No scheduler exists for the escalation
sweep; it's exposed as `POST /api/leave-requests/escalate` (manual or
external-cron trigger) rather than adding a background-job dependency
before it's needed.

### Payroll engine

Full formula and edge cases are in `docs/PAYROLL.md`. The two day-count
bases are deliberately different — mid-month join/exit proration uses
calendar days (a flat salary "covers" every day of the month), while
unpaid-leave deduction uses working days (leave only costs you a day
you'd otherwise have worked) — worth reading before it looks like a bug.
Tax is marginal/progressive specifically so a salary one dollar over a
bracket boundary is never worse off than one dollar under it;
`test_no_cliff_at_bracket_boundary` in `test_tax.py` demonstrates this
directly. Needed no schema changes beyond what the initial migration
already had — the `payroll_entries` columns matched the calculation
pipeline once it was designed.

### Dashboard UI

No framework, no build step, no bundler — each JS file defines one global
(`Api`, `Store`, `Dom`, `Format`, `Employees`, `Leave`, `Payroll`,
`Dashboard`, `Nav`) via an IIFE, and `<script>` load order in `index.html`
is the only wiring. All user-supplied free text (names, reasons, decision
notes) goes through `Dom.escapeHtml` before being interpolated into
template-string HTML — there's no framework auto-escaping innerHTML here,
so this is load-bearing against XSS, not decorative.

Caught a real bug by actually driving the dashboard in a browser
(Playwright, headless, against the dockerized stack) rather than just
reading the code: the employee-cache fetch requested `per_page: 200`, but
`EmployeeListQuerySchema` caps `per_page` at 100 — every dropdown that
needed the employee list (manager picker, "acting as" selector) 400'd
unconditionally, on every load, regardless of how many employees actually
existed. Fixed in `main.js` and `employees.js`. A pure code read would
likely have missed this — the number "200" reads as fine until it's
checked against the schema's actual `validate.Range(max=100)`.

Also caught while doing that same browser test: `docker compose up`
brought up a backend with an empty schema — migrations were never run
automatically, so every API call 500'd until `flask db upgrade` was run by
hand inside the container. Fixed with `backend/docker-entrypoint.sh` (runs
`flask db upgrade` before `exec`'ing into gunicorn). One gotcha worth
knowing if you touch it: docker-compose bind-mounts `./backend` over
`/app` at runtime, so the image's `RUN chmod +x` at build time is
irrelevant — the executable bit has to exist on the **host** file, or the
container fails to start with "permission denied".

### Auth & RBAC

Full matrix and identity model in `docs/AUTH.md`. The headline design
decision: the service layer (`LeaveService`, `PayrollService`) never
learns about JWTs or roles at all — it just takes an employee id like it
always did. All identity derivation (who is this request acting as, and
is an override allowed) lives in the API layer instead, keeping the
boundary between "who is calling" and "what business rule applies" a hard
line. `user_lookup_loader` re-fetches the `User` row from the DB on every
request rather than trusting JWT claims, so deactivating an account
revokes access on the very next request, not just at token expiry — see
`test_deactivated_user_token_is_rejected_on_next_request`.

One deliberate tightening: an orphan employee (no manager on record) used
to be approvable by "any active employee" as a stopgap before real
authorization existed. That's now a hard `ForbiddenError` for everyone
except an Admin using the explicit `bypass_authorization` override — a
real permission boundary instead of "whoever happens to click first."

Bootstrapping the first Admin account is a `flask create-admin` CLI
command, not an API endpoint — creating a user via the API requires
already being an Admin, so something has to break that cycle by writing
to the DB directly. `--if-not-exists` makes it safe to run unconditionally
on every container start (see `docker-entrypoint.sh`), rather than
needing a one-time manual step a fresh clone would have to know about.

### Deployment & sample data

`flask seed-demo` (`backend/app/seed.py`) builds the sample dataset
entirely through the same service layer the API uses — every leave
request still goes through overlap detection and balance validation, the
payroll period is still generated and finalized through the real formula
— rather than hand-inserted rows that could silently drift out of sync
with the rules in docs/LEAVE.md and docs/PAYROLL.md as those evolve.
`database/dump.sql` is that dataset's `pg_dump` output, restore-tested
against a throwaway database before committing it (see
`database/README.md`); the Admin account is deliberately excluded from it
so no bootstrap credential ends up baked into a committed file. Also
stripped `pg_dump` 16.x's `\restrict`/`\unrestrict` marker lines from the
committed dump — they're a psql-client-version-specific safety feature,
not schema or data, and a client from a different Postgres release can
choke on them.

### Single-service hosting

The root-level `Dockerfile` (distinct from `backend/Dockerfile` and
`frontend/Dockerfile`, which local docker-compose still uses unchanged)
builds one image that serves both the API and the static dashboard from a
single Flask process — no nginx, no second service, no CORS to configure.
`app/frontend.py`'s `register_frontend()` only activates if
`FRONTEND_DIST_DIR` points at a real directory, so it's a no-op locally
and in every test; it only does anything inside that specific image,
where the frontend is copied to `/static_frontend` at build time. The
gunicorn bind address reads `$PORT` from the environment (defaulting to
5000) since most free-tier PaaS hosts assign that dynamically rather than
letting you pick a fixed port. Full walkthrough: `docs/HOSTING.md`.
