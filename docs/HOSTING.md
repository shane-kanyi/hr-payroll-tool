# Hosting a live instance (Render, free tier)

This is the quickest path to a public URL for the app, using
[Render](https://render.com)'s free web service + free PostgreSQL. Render
changes its exact free-tier terms occasionally, so double-check current
pricing/limits when you sign up — as of writing, both the web service and
the database have a genuinely free tier, no card required to start.

Two things worth knowing going in:

- **The free web service sleeps after 15 minutes of no traffic** and takes
  ~30-50 seconds to wake back up on the next request. The first load after
  a period of inactivity will feel slow — that's this, not a bug.
- **The free Postgres database expires 30 days after creation.** Fine for
  a demo/evaluation window; if you need it longer, recreate the database
  (or upgrade the plan) before it expires.

## Why one service instead of three

Locally, `docker compose` runs three containers — Postgres, the Flask API,
and an nginx container serving the frontend and proxying `/api/*` to the
API. For a free single-instance deploy, that's two more moving parts than
necessary. The root-level `Dockerfile` (separate from `backend/Dockerfile`
and `frontend/Dockerfile`, which docker-compose still uses unchanged)
builds one image that serves both: Flask serves the API under `/api/*`
and the static dashboard files under everything else, from one process on
one port. No second service, no CORS configuration, no proxy to wire up.

## Option A: one-click Blueprint (fastest)

1. Push this repository to your own GitHub account (fork it, or push it
   as a new repo — Render deploys from a repo it can see).
2. In Render: **New** → **Blueprint**, then connect that repository.
   Render reads `render.yaml` at the repo root and proposes creating:
   - a free Postgres database (`hr-payroll-db`)
   - a free web service (`hr-payroll-tool`) built from the root
     `Dockerfile`, wired to that database's connection string
     automatically, with `SECRET_KEY`/`JWT_SECRET_KEY` auto-generated
3. Render will prompt you for one value it deliberately doesn't
   auto-fill: `ADMIN_PASSWORD`. Set it to something you'll remember (not
   the repo's local dev default).
4. Click **Apply**. First deploy takes a few minutes (installing
   dependencies, then running migrations on startup).
5. Once live, open the service's URL — that's both the dashboard and the
   API, same origin. Log in with `admin@example.com` and the password you
   set in step 3.

If `render.yaml`'s exact syntax has drifted from what your Render account
expects (Render's Blueprint format does change over time), fall back to
Option B below — it's the same end result, just click-through instead of
file-driven.

## Option B: manual setup through the dashboard

1. **Database first.** Render dashboard → **New** → **PostgreSQL**. Name
   it whatever you like, free plan, create it. Once it's up, copy its
   **Internal Database URL** (starts with `postgresql://`) — you'll need
   it in step 3.
2. **New** → **Web Service** → connect this repository.
3. Configure the service:
   - **Runtime**: Docker
   - **Dockerfile Path**: `./Dockerfile` (the one at the repo root, not
     `backend/Dockerfile`)
   - **Plan**: Free
   - **Health Check Path**: `/api/health`
4. Add environment variables (Render's "Environment" tab):
   | Key | Value |
   |---|---|
   | `DATABASE_URL` | the Internal Database URL from step 1 |
   | `SECRET_KEY` | any long random string |
   | `JWT_SECRET_KEY` | any long random string, different from the above |
   | `ADMIN_EMAIL` | `admin@example.com` (or your own) |
   | `ADMIN_PASSWORD` | a password you'll remember |
5. Create the service. Render builds the image and starts it; watch the
   deploy log for `Running upgrade ... -> ...` (migrations) and `Created
   admin user ...` — both run automatically on every start via
   `backend/docker-entrypoint.sh`, so there's nothing else to run by hand.
6. Open the service's public URL and log in.

## Loading sample data (optional)

A fresh deploy has an Admin account and nothing else — an empty database.
To load the same sample teams/employees/leave requests/payroll period
used to produce `database/dump.sql`:

Render's dashboard has a **Shell** tab on the web service (a terminal into
the running container). Open it and run:

```bash
flask seed-demo
```

That's the same command documented in the main README for local use — it
only needs a live shell into the deployed container, nothing
deploy-specific.

## Updating the live instance

Render redeploys automatically on every push to the branch it's watching
(configurable in the service's settings). No extra step needed beyond
pushing your changes.

## If you'd rather not use Render

The same root `Dockerfile` works on any Docker-based host that lets you
attach a Postgres instance and set environment variables the same way —
[Railway](https://railway.app) is a common alternative with a similar
free-trial-then-paid model and an almost identical setup flow (connect
repo, add a Postgres plugin, set the same env vars, deploy). The
Dockerfile and environment variables above don't change between them.
