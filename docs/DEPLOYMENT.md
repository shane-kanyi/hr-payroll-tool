# Deployment

## Local / evaluation (docker-compose)

```bash
cp backend/.env.example backend/.env
docker compose up --build
```

This brings up three containers — `db` (Postgres 16), `backend` (Flask +
gunicorn), `frontend` (nginx serving the static dashboard and proxying
`/api/*` to the backend). On every start, `backend/docker-entrypoint.sh`:

1. Runs `flask db upgrade` — applies any migration not yet applied. Safe
   to run on every start; a no-op once the schema is current.
2. Runs `flask create-admin --if-not-exists` using `ADMIN_EMAIL` /
   `ADMIN_PASSWORD` from the environment — creates the first Admin login
   if none exists yet, skips silently otherwise.
3. Starts gunicorn.

There is no sample data (employees/teams/leave/payroll) in a fresh
`docker compose up` — only the Admin account. To load the same sample
data used to produce `database/dump.sql`, either:

```bash
docker compose exec backend flask seed-demo
```

or restore `database/dump.sql` directly (see `database/README.md`) —
faster, since it skips re-running every business rule, but only reflects
the schema at the time the dump was taken (re-run `seed-demo` on a fresh
DB if you want the *current* code's version of the sample data instead).

- API: `http://localhost:5000/api/health`
- Frontend: `http://localhost:8080`

## Environment variables

All have working defaults for local use (see `backend/.env.example`); only
`ADMIN_PASSWORD` genuinely needs changing before anything beyond local
evaluation.

| Variable | Default | Notes |
|---|---|---|
| `SECRET_KEY` | `dev-secret-key` | Flask session/signing secret. |
| `DATABASE_URL` | local Postgres | SQLAlchemy connection string. |
| `JWT_SECRET_KEY` | dev value | Signs auth tokens — **must** be changed and kept secret outside local use. |
| `JWT_ACCESS_TOKEN_EXPIRES_MINUTES` | `60` | Access token lifetime. No refresh tokens exist yet (see docs/AUTH.md) — a shorter value here has no way to be silently renewed. |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | `admin@example.com` / `ChangeMe123!` | Bootstrap Admin account, created on first container start. **Change the password** (or unset both and run `flask create-admin` manually with your own) before this is reachable by anyone but you. |
| `SOCIAL_SECURITY_RATE` | `0.06` | See docs/PAYROLL.md. |
| `ANNUAL_LEAVE_DAYS_PER_YEAR` / `SICK_LEAVE_DAYS_PER_YEAR` | `21` / `10` | See docs/LEAVE.md. |
| `LEAVE_MIN_NOTICE_BUSINESS_DAYS` | `3` | See docs/LEAVE.md. |
| `LEAVE_ESCALATION_THRESHOLD_DAYS` | `3` | See docs/LEAVE.md. |
| `LEAVE_TEAM_MIN_COVERAGE_RATIO` | `0.5` | See docs/LEAVE.md. |

## Before deploying anywhere real (checklist)

This project was built as a scoped coding exercise, not hardened for
production. If it were going further, in rough priority order:

1. **Change `ADMIN_PASSWORD`, `SECRET_KEY`, `JWT_SECRET_KEY`.** All three
   ship with public, documented defaults, by design, for a zero-friction
   local evaluation experience — none are safe to reuse anywhere reachable
   by anyone else.
2. **Restrict CORS.** `cors.init_app(app, resources={r"/api/*": {"origins": "*"}})`
   in `app/__init__.py` allows any origin. Fine for local dev against a
   same-machine frontend; should be pinned to the actual frontend origin
   otherwise.
3. **Turn off `FLASK_DEBUG`.** `docker-compose.yml`'s `backend/.env`
   ships `FLASK_DEBUG=1`, which leaks stack traces on unhandled
   exceptions — set `FLASK_ENV=production` / `FLASK_DEBUG=0`.
4. **Put a real WSGI front door in place of the dev bind.** Gunicorn is
   already used (not Flask's dev server), but there's no reverse proxy /
   TLS termination here — that's expected to be handled by whatever
   sits in front of this stack (a cloud load balancer, a separate nginx,
   etc.), not something this repo provides.
5. **Add refresh tokens or shorten the access-token lifetime further.**
   Documented as a known simplification in docs/AUTH.md — one token,
   60 minutes, no revocation list beyond "is the account still active."
6. **Database backups / point-in-time recovery** for the Postgres
   volume — `docker-compose.yml`'s named volume has no backup strategy
   attached; that's infrastructure-specific and out of scope here.
7. **Migrations in production**: `flask db upgrade` runs automatically on
   every container start (see above). That's convenient for a small
   single-instance deployment; a multi-instance rollout would want
   migrations run once, out-of-band, before the new instances start,
   to avoid two containers racing to run the same migration.

## CI

No CI workflow is included — out of scope for this exercise (see the
stretch-goals discussion in the top-level README). `pytest` (backend) and
manual/Playwright-driven browser checks (frontend) are the two things a CI
pipeline would run; both are documented above and in `backend/README`-style
instructions in the top-level README's "Running tests" section.
