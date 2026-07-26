# API Reference

All responses are JSON. Successful responses wrap the payload in `data`
(and `meta` for paginated lists). Errors return `{"message": "...", ...}`
with an appropriate status code (400 validation, 404 not found, 409
conflict, 500 unexpected).

## Health

`GET /api/health` → `{"status": "ok", "database": "ok" | "error: ..."}`

## Teams

| Method | Path | Body | Notes |
|---|---|---|---|
| GET | `/api/teams` | — | List all teams |
| POST | `/api/teams` | `{"name": str}` | 409 if name already exists |
| GET | `/api/teams/<id>` | — | 404 if not found |

## Employees

| Method | Path | Body | Notes |
|---|---|---|---|
| GET | `/api/employees` | — | Query params below |
| POST | `/api/employees` | see below | |
| GET | `/api/employees/<id>` | — | 404 if not found |
| PUT | `/api/employees/<id>` | partial, same fields as create | `is_active` not accepted here — see safeguards |
| POST | `/api/employees/<id>/deactivate` | — | 409 if already inactive, or still manages active reports |
| POST | `/api/employees/<id>/reactivate` | — | 409 if already active |
| GET | `/api/employees/org-chart` | — | `?include_inactive=true` to include deactivated employees |

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

Full rules and assumptions: `docs/LEAVE.md`. Auth isn't wired up yet
(Phase 6), so `acting_manager_id` / `actor_employee_id` are passed
explicitly in request bodies as an interim stand-in for a real caller
identity.

| Method | Path | Body | Notes |
|---|---|---|---|
| GET | `/api/leave-requests` | — | Filters: `employee_id`, `manager_id`, `status`, `escalated_only`, `page`, `per_page` |
| POST | `/api/leave-requests` | see below | Submit a request |
| GET | `/api/leave-requests/<id>` | — | 404 if not found |
| POST | `/api/leave-requests/<id>/approve` | `{"acting_manager_id": int, "notes"?: str}` | See safeguards |
| POST | `/api/leave-requests/<id>/reject` | `{"acting_manager_id": int, "notes"?: str}` | |
| POST | `/api/leave-requests/<id>/cancel` | `{"actor_employee_id": int}` | Only the requester, only while `pending` |
| GET | `/api/leave-requests/pending-approvals?manager_id=<id>` | — | Direct reports' pending requests + escalated skip-level requests |
| GET | `/api/leave-requests/on-leave?date=YYYY-MM-DD` | — | Who's approved-on-leave on a given date (default today) |
| GET | `/api/leave-requests/balances?employee_id=<id>&year=<yyyy>` | — | Auto-provisions ANNUAL/SICK balances for that year if missing |
| POST | `/api/leave-requests/escalate` | — | Runs the escalation sweep now (cron/manual trigger; no scheduler yet) |

### Submit body

```json
{
  "employee_id": 3,
  "leave_type": "annual",
  "start_date": "2026-08-10",
  "end_date": "2026-08-14",
  "reason": "Family trip"
}
```

`leave_type` is one of `annual`, `sick`, `unpaid`. `days_requested` is
computed server-side (business days, inclusive) — not accepted as input.

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

Full formula, brackets, and edge-case handling: `docs/PAYROLL.md`.

| Method | Path | Body | Notes |
|---|---|---|---|
| POST | `/api/payroll/generate` | `{"year": int, "month": int, "generated_by_id"?: int}` | Creates the period (draft) if new; recomputes all entries if still draft; `409` if already finalized |
| POST | `/api/payroll/periods/<id>/finalize` | — | Locks the period; `409` if already finalized, `400` if it has no entries |
| GET | `/api/payroll/periods` | — | Paginated, newest first. `page`, `per_page` |
| GET | `/api/payroll/periods/<id>` | — | 404 if not found |
| GET | `/api/payroll/periods/<id>/entries` | — | `?employee_id=` to filter to one employee |
| GET | `/api/payroll/periods/<id>/entries/<employee_id>` | — | Single payslip; 404 if that employee has no entry in this period |
| GET | `/api/payroll/employees/<employee_id>/entries` | — | All of one employee's payslips across every period (payroll history) |

### Business-rule error responses worth knowing about

- Regenerating a finalized period → `409` (historical payroll is
  immutable — see docs/PAYROLL.md snapshot section).
- Finalizing an already-finalized period → `409`.
- Finalizing a period with zero entries (e.g. no eligible employees) →
  `400`.
- An employee deactivated entirely before a period started, or not yet
  hired by the time it ends, simply has no entry for that period (not an
  error — check for a 404 on the single-payslip endpoint).
