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
