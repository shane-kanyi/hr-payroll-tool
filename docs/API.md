# API Reference

All responses are JSON. Successful responses wrap the payload in `data`
(and `meta` for paginated lists). Errors return `{"message": "...", ...}`
with an appropriate status code (400 validation, 401 unauthenticated, 403
forbidden/wrong role, 404 not found, 409 conflict, 500 unexpected).

Every endpoint below except `/api/health` and `/api/auth/login` requires
`Authorization: Bearer <token>` from a successful login. Full RBAC matrix
and the identity-derivation model: `docs/AUTH.md`.

## Health

`GET /api/health` → `{"status": "ok", "database": "ok" | "error: ..."}`

## Auth

| Method | Path | Body | Notes | Role |
|---|---|---|---|---|
| POST | `/api/auth/login` | `{"email": str, "password": str}` | Returns `{access_token, user}`; 401 on bad credentials or a deactivated account | none |
| GET | `/api/auth/me` | — | The logged-in user | any |
| GET | `/api/auth/users` | — | List all user accounts | Admin |
| POST | `/api/auth/users` | `{"email", "password", "role", "employee_id"?}` | `role` one of `admin`/`manager`/`employee`; 409 if email or `employee_id` already taken | Admin |
| POST | `/api/auth/users/<id>/deactivate` | — | Revokes access on their *next* request, not just next login — see docs/AUTH.md | Admin |
| POST | `/api/auth/users/<id>/reactivate` | — | | Admin |

Bootstrapping the very first Admin account (chicken-and-egg problem, since
creating a user requires being one) is a CLI command, not an API endpoint:
`flask create-admin --email ... --password ...` — see docs/AUTH.md.

## Teams

| Method | Path | Body | Notes | Role |
|---|---|---|---|---|
| GET | `/api/teams` | — | List all teams | any |
| POST | `/api/teams` | `{"name": str}` | 409 if name already exists | Admin |
| GET | `/api/teams/<id>` | — | 404 if not found | any |

## Employees

| Method | Path | Body | Notes | Role |
|---|---|---|---|---|
| GET | `/api/employees` | — | Query params below | any |
| POST | `/api/employees` | see below | | Admin |
| GET | `/api/employees/<id>` | — | 404 if not found | any |
| PUT | `/api/employees/<id>` | partial, same fields as create | `is_active` not accepted here — see safeguards | Admin |
| POST | `/api/employees/<id>/deactivate` | — | 409 if already inactive, or still manages active reports | Admin |
| POST | `/api/employees/<id>/reactivate` | — | 409 if already active | Admin |
| GET | `/api/employees/org-chart` | — | `?include_inactive=true` to include deactivated employees | any |

### List query params (`GET /api/employees`)

- `is_active` (bool)
- `team_id` (int)
- `manager_id` (int)
- `search` (string, matches name, case-insensitive substring)
- `page` (int, default 1)
- `per_page` (int, default 20, max 100)

### Create/update body

```json
{
  "name": "Jane Doe",
  "role": "Engineer",
  "team_id": 1,
  "manager_id": 2,
  "start_date": "2025-01-01",
  "salary": "5000.00",
  "employment_type": "full_time"
}
```

`employment_type` is one of `full_time`, `part_time`, `contract`.
`team_id` and `manager_id` are optional and nullable. All fields are
optional on update (partial patch semantics), required on create except
`team_id`/`manager_id`.

### Business-rule error responses worth knowing about

- Creating/updating with a `manager_id` that would close a reporting loop
  (including self-management) → `400` from the update, not a 500 or a
  silently-accepted bad state.
- Deactivating an employee who still manages active reports → `409` with
  `blocking_reports: [id, ...]` listing who needs reassigning first.
- Deactivating/reactivating something already in that state → `409`.

## Leave Requests

Full rules and assumptions: `docs/LEAVE.md`. `employee_id`
(submit) / `acting_manager_id` (approve/reject) / `actor_employee_id`
(cancel) are derived from the logged-in user and **not** read from the
request body — except for Admins, who may still pass them explicitly to
act on behalf of any employee (see docs/AUTH.md).

| Method | Path | Body | Notes | Role |
|---|---|---|---|---|
| GET | `/api/leave-requests` | — | Filters: `employee_id`, `manager_id`, `status`, `escalated_only`, `page`, `per_page`. Non-admins are always forced to their own `employee_id` regardless of the query string | any (scoped) |
| POST | `/api/leave-requests` | see below | Submit a request | any |
| GET | `/api/leave-requests/<id>` | — | 404 if not found; 403 unless you're the owner, their manager, or Admin | any (scoped) |
| POST | `/api/leave-requests/<id>/approve` | `{"notes"?: str}` (Admin may add `"acting_manager_id"`) | See safeguards | Admin, Manager |
| POST | `/api/leave-requests/<id>/reject` | same as approve | | Admin, Manager |
| POST | `/api/leave-requests/<id>/cancel` | `{}` (Admin may add `"actor_employee_id"`) | Only the requester, only while `pending` | any |
| GET | `/api/leave-requests/pending-approvals?manager_id=<id>` | — | Managers are forced to their own id; Admin must supply `manager_id` | Admin, Manager |
| GET | `/api/leave-requests/on-leave?date=YYYY-MM-DD` | — | Who's approved-on-leave on a given date (default today) | any |
| GET | `/api/leave-requests/balances?employee_id=<id>&year=<yyyy>` | — | Non-admins always get their own; Admin must supply `employee_id` | any (scoped) |
| POST | `/api/leave-requests/escalate` | — | Runs the escalation sweep now (cron/manual trigger; no scheduler yet) | Admin |

### Submit body

```json
{
  "leave_type": "annual",
  "start_date": "2026-08-10",
  "end_date": "2026-08-14",
  "reason": "Family trip"
}
```

`leave_type` is one of `annual`, `sick`, `unpaid`. `days_requested` is
computed server-side (business days, inclusive) — not accepted as input.
Admins may add `"employee_id": <int>` to submit on behalf of someone else;
everyone else always submits as themselves.

### Business-rule error responses worth knowing about

- Overlapping an existing pending/approved request for the same employee →
  `409` with `conflicting_request_ids: [id, ...]`.
- Annual leave submitted with less than the minimum notice → `400`.
- Insufficient ANNUAL/SICK balance at submission *or* approval time → `400`.
- A request spanning a calendar-year boundary → `400` (split into two).
- Approving/rejecting your own request → `403`.
- Approving/rejecting without authority over the request (not the manager,
  and not an escalated skip-level manager) → `403`.
- Approving something that would drop team coverage below 50% → `409` with
  `team_size` / `available_after`.
- Acting on a request that's already been decided → `409`.
- Cancelling someone else's request, or a non-pending one → `403` / `409`.

## Payroll

Full formula, brackets, and edge-case handling: `docs/PAYROLL.md`. Payroll
is treated as more sensitive than leave — Managers get no cross-employee
visibility here at all, only their own payslip (see docs/AUTH.md).

| Method | Path | Body | Notes | Role |
|---|---|---|---|---|
| POST | `/api/payroll/generate` | `{"year": int, "month": int}` | Creates the period (draft) if new; recomputes all entries if still draft; `409` if already finalized. `generated_by_id` is always the caller, never client-supplied | Admin |
| POST | `/api/payroll/periods/<id>/finalize` | — | Locks the period; `409` if already finalized, `400` if it has no entries | Admin |
| GET | `/api/payroll/periods` | — | Paginated, newest first. `page`, `per_page` | Admin |
| GET | `/api/payroll/periods/<id>` | — | 404 if not found | Admin |
| GET | `/api/payroll/periods/<id>/entries` | — | `?employee_id=` to filter to one employee | Admin |
| GET | `/api/payroll/periods/<id>/entries/<employee_id>` | — | Single payslip; 404 if that employee has no entry in this period; 403 unless it's your own or you're Admin | any (scoped) |
| GET | `/api/payroll/employees/<employee_id>/entries` | — | All of one employee's payslips across every period; 403 unless it's your own or you're Admin | any (scoped) |

### Business-rule error responses worth knowing about

- Regenerating a finalized period → `409` (historical payroll is
  immutable — see docs/PAYROLL.md snapshot section).
- Finalizing an already-finalized period → `409`.
- Finalizing a period with zero entries (e.g. no eligible employees) →
  `400`.
- An employee deactivated entirely before a period started, or not yet
  hired by the time it ends, simply has no entry for that period (not an
  error — check for a 404 on the single-payslip endpoint).
