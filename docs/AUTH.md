# Authentication & RBAC

## Roles

Exactly three, backed by the `roles`/`users` tables (a DB `CHECK`
constraint restricts `roles.name` to these values — migration
`598c1b53ccb8`):

- **admin** — HR/ops. Full access, including acting on behalf of any
  employee.
- **manager** — approves/rejects leave for their own direct (and, once
  escalated, skip-level) reports. Otherwise behaves like an employee.
- **employee** — manages their own leave and views their own data.

## Auth mechanics

- `POST /api/auth/login` issues a JWT (`Flask-JWT-Extended`) on successful
  email+password check (`werkzeug.security` hashing — no new dependency).
- A `user_lookup_loader` (registered in `app/__init__.py`) re-fetches the
  `User` row from the database **on every request** rather than trusting
  the JWT's claims. This is a deliberate choice over pure claims-based auth:
  it means deactivating a user's account takes effect on their very next
  request, not just after their token happens to expire. See
  `test_deactivated_user_token_is_rejected_on_next_request` in
  `test_auth_api.py`.
- No refresh tokens / token blocklist. A single access token
  (`JWT_ACCESS_TOKEN_EXPIRES_MINUTES`, default 60) is enough for the
  current scope — documented simplification, not an oversight.
- `Role` rows are created lazily (`RoleRepository.get_or_create`) the first
  time they're referenced, so there's no separate "seed roles" migration
  step to forget.

## Bootstrapping the first Admin

Creating a user normally requires being logged in as an Admin
(`POST /api/auth/users`) — which is a chicken-and-egg problem on a fresh
database. `flask create-admin --email ... --password ... [--if-not-exists]`
exists purely to break that: it writes directly to the DB, bypassing the
API/RBAC entirely, and is meant to be run once per environment (or, with
`--if-not-exists`, safely on every container start — see
`backend/docker-entrypoint.sh` and the `ADMIN_EMAIL`/`ADMIN_PASSWORD`
env vars in `.env.example`). **The shipped defaults are for local/demo use
only** — change the password (or unset the env vars and create the admin
manually) before deploying anywhere real.

## RBAC matrix

| Action | Admin | Manager | Employee |
|---|---|---|---|
| View employees / org chart | ✓ | ✓ | ✓ |
| Create/update/deactivate/reactivate employees, create teams | ✓ | ✗ | ✗ |
| Submit / cancel leave | ✓ (any employee, via override) | ✓ (self) | ✓ (self) |
| Approve / reject leave | ✓ (bypasses the manager-chain check) | ✓ (own reports / escalated skip-level reports, per docs/LEAVE.md) | ✗ |
| View own leave requests / balances | ✓ | ✓ | ✓ |
| View someone else's leave requests / balances | ✓ | ✗ | ✗ |
| Who's on leave today | ✓ | ✓ | ✓ |
| Run the escalation sweep | ✓ | ✗ | ✗ |
| Generate / finalize payroll, view all periods/entries | ✓ | ✗ | ✗ |
| View own payslips | ✓ | ✓ | ✓ |
| View someone else's payslip | ✓ | ✗ | ✗ |
| Manage user accounts (`/api/auth/users`) | ✓ | ✗ | ✗ |

Two rows worth calling out:

- **Payroll is stricter than leave.** A Manager can see their reports'
  leave-approval queue, but *cannot* see their reports' payslips — only
  their own. Payroll numbers are treated as more sensitive than leave
  status, so only Admin gets cross-employee visibility there.
- **Employees have zero leave-approval visibility**, even for their own
  team, since they don't manage anyone by definition of the role.

## The identity-derivation model (why service signatures didn't change)

`LeaveService`/`PayrollService` take `acting_manager_id` / `employee_id` /
`actor_employee_id` / `generated_by_id` as plain parameters — they have no
concept of HTTP auth, JWTs, or roles at all. All identity-derivation logic
lives in the API layer (`app/api/leave.py`, `app/api/payroll.py`) instead,
which is exactly where it belongs in a layered architecture: the boundary
between "who is calling" and "what business rule applies" stays a hard
line, and the service layer can be exercised directly in tests without
ever touching auth.

- **Non-admins always act as themselves.** `employee_id` is derived from
  `current_user().employee_id` and any client-supplied value is ignored.
- **Admins may pass an explicit override** (`employee_id`,
  `acting_manager_id`, `actor_employee_id` in the request body) to act on
  behalf of any employee — HR entering leave for someone, or resolving an
  orphan employee's request that has no manager to decide it (see
  `LeaveService._authorize_decision` and the `bypass_authorization` /
  `bypass_ownership` flags it and `cancel_leave_request` now accept).
- **An Admin with no linked `Employee` record has no implicit "self".**
  Submitting/cancelling/approving as an unlinked Admin *requires* the
  explicit override — there's deliberately no silent fallback to "act as
  nobody in particular." See
  `test_admin_can_cancel_any_pending_request` in `test_leave_api.py`.
- **`PayrollService.generate_payroll`'s `generated_by_id`** is simpler: no
  override needed, it's purely an audit trail, always set from the calling
  Admin's own `employee_id` (which may legitimately be `None`).

## Why an orphan employee's request can't be approved by "just anyone"

`_authorize_decision` deliberately does *not* fall back to "any active
employee" when an employee has no manager anywhere in their chain — that
would mean whoever happens to click first gets to decide someone else's
leave, which is not a real permission boundary. Instead it raises
`ForbiddenError` for any non-admin in that situation, and resolving it
requires an Admin's `bypass_authorization` override
(`test_orphan_employee_with_no_manager_blocks_ordinary_approvers` /
`test_admin_bypass_authorization_can_decide_orphan_employee_request`).

## Frontend: how login replaced the "acting as" selector

The dashboard's `api.js` fetch wrapper has always read an `access_token`
from `localStorage` — now there's a real login screen behind it:

- A login screen gates the whole app; `GET /api/auth/me` resumes a session
  from a stored token on page load, and a 401 anywhere bounces back to
  login (`Api.onUnauthorized`).
- An "Acting as" selector — which would otherwise have to exist for every
  role, since there's no other way to say "who am I" without login — is
  scoped down to exactly what it's for now: an **Admin-only** override
  inside the Leave tab, used to act on behalf of a specific employee.
  Every other role has no selector at all; their identity comes from who
  they logged in as.
- The Employees tab's create/deactivate/reactivate controls, and the
  Payroll tab's generate/finalize/all-periods views, are hidden (not just
  disabled) for non-Admins — matching what the backend would 403 anyway,
  so the UI doesn't offer buttons that can't work.
