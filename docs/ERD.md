# Entity Relationship Diagram

teams (1) ──< employees (self-referential: manager_id -> employees.id)
                  │  │  │
                  │  │  └──< leave_balances
                  │  └─────< leave_requests (employee_id, decided_by_id both -> employees.id)
                  └────────< payroll_entries
                  └────────< users (employee_id, nullable, unique)

roles (1) ──< users
payroll_periods (1) ──< payroll_entries
users (1) ──< audit_logs (actor_user_id, nullable)

## Design choices worth flagging

- Numeric, not Float, for every money/day-count column — floating point
  rounding is unacceptable in payroll math.
- Postgres ENUM types for status/type columns instead of plain strings,
  for DB-level validation. Trade-off: adding a new enum value later needs
  a migration with `ALTER TYPE ... ADD VALUE`.
- DB-level constraints only cover facts true of a single row in isolation
  (end_date >= start_date, non-negative salary). Rules needing other rows
  (leave overlap, balance sufficiency, self-approval) belong in the
  service layer — Phase 3.
- `leave_requests.escalated_at` (added in Phase 3, migration
  `630b8660218e`) is nullable and set once by the escalation sweep; it's a
  one-way flag, never cleared. See `docs/LEAVE.md` for the full escalation
  rule and why it exists alongside `decided_by_id`/`decided_at` rather than
  replacing them.