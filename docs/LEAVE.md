# Leave Management: Business Rules & Assumptions

This documents the "spreadsheet problems" the leave engine targets and the
concrete rule implemented for each, per `app/services/leave_service.py`.

## Data model

- `LeaveRequest`: one row per request, `status` in
  `pending | approved | rejected | cancelled`. Never deleted.
- `LeaveBalance`: one row per `(employee, leave_type, year)`, tracking
  `allocated_days` / `used_days`. Auto-provisioned lazily (see below) rather
  than requiring an upfront admin seeding step.
- `escalated_at` on `LeaveRequest`: set once a pending request has aged past
  the escalation threshold (see "Escalation" below). Nullable, one-way.

## Problems identified, and what was built

### 1. Double-booking / overlapping leave

A spreadsheet won't stop the same person submitting two overlapping
requests, or a manager approving a second request that overlaps one they
already approved last week.

**Rule:** `submit_leave_request` rejects (409) any new request that overlaps
an existing `pending` or `approved` request for the same employee.
`approve_leave_request` re-checks overlap against `approved` requests only,
immediately before approving — this catches the race where two *different*
pending requests for the same employee didn't overlap each other at
submission time but one was approved in between (e.g. request A for the 8th
was submitted, then request B for the 9th-10th was submitted before A was
decided; if A is later approved for the 8th-9th, B now conflicts and is
blocked at approval time even though it passed at submission time).

### 2. Leave balance validation

**Rule:** `ANNUAL` and `SICK` leave draw against a yearly balance
(`LeaveBalance.remaining_days = allocated - used`); submitting or approving
a request that would exceed the remaining balance is rejected (400).
`UNPAID` leave has no balance — it's always available, and instead reduces
pay (see "Payroll interaction" below). This is a deliberate three-way split:
paid leave is finite and tracked, unpaid leave is a pay decision, not a
"do you have enough" decision.

**Balances are provisioned lazily**, not via an upfront seeding step: the
first time a balance is needed (on submit, approve, or a dashboard read) and
none exists for that `(employee, leave_type, year)`, one is created using
`ANNUAL_LEAVE_DAYS_PER_YEAR` / `SICK_LEAVE_DAYS_PER_YEAR` (config, default
21 / 10). If the employee's `start_date` falls inside the requested year,
the allocation is **prorated** by the fraction of the year remaining from
their start date — a June 2 joiner gets roughly half the annual allocation
for that year, not the full amount. Employees not yet hired in a given year
get a zero allocation for it.

### 3. Not enough notice given

Spreadsheets don't stop someone requesting tomorrow off with no lead time,
leaving a manager to approve/reject under time pressure or just miss it.

**Rule:** `ANNUAL` leave requires at least `LEAVE_MIN_NOTICE_BUSINESS_DAYS`
(config, default 3) business days' notice — rejected at submission (400)
otherwise. `SICK` and `UNPAID` are exempt: sickness is unplanned by
definition, and unpaid leave is frequently used for the same kind of
short-notice personal emergency.

### 4. A team getting under-covered

A spreadsheet has no concept of "how many of this team are out at once" — it
will happily let a manager approve leave for half the team the same week.

**Rule:** on **approval** (not submission — a request shouldn't be blocked
from ever being *considered* just because of coverage; that's the manager's
call to weigh, but the system won't let them approve past the line), if the
employee has a team, the service computes how many active team members
would be simultaneously on approved leave including this request. If fewer
than `LEAVE_TEAM_MIN_COVERAGE_RATIO` (config, default 50%) of the team would
remain available, the approval is rejected (409) with the team size and
post-approval availability in the response payload, so the UI can explain
why. **Solo-member teams (team size < 2) are exempt** — there's no
"coverage" concept to protect when there's no one else on the team, and
blocking the one person on a team from ever taking leave would be an
obviously wrong outcome of a literal reading of the rule.

### 5. Unresolved requests sitting unanswered

A request lost in a spreadsheet or a WhatsApp thread might just never get
answered.

**Rule:** `run_escalation_sweep()` finds `pending` requests older than
`LEAVE_ESCALATION_THRESHOLD_DAYS` (config, default 3 days) and stamps
`escalated_at`. From that point, the requester's **skip-level manager**
(their manager's manager) may also approve or reject it — the original
manager keeps the ability to act too, since escalation is meant to add a
safety net, not take away their authority. There's no scheduler wired up yet
(no Celery/APScheduler in this phase), so the sweep is exposed as
`POST /api/leave-requests/escalate` to be triggered by an external cron, or
manually. Phase 7 (stretch: notifications) is the natural place to wire this
to an actual scheduled job and an email/Slack alert.

### 6. Manager self-approval

**Rule:** an employee can never decide their own leave request, even if
they happen to have no other approver in their chain — checked before
anything else in `_prepare_decision`.

### 7. Insufficient / missing approval authority

Two distinct failure modes, both handled:

- **Wrong person deciding:** only the employee's direct manager (or, once
  escalated, their skip-level manager) may approve/reject. Anyone else gets
  403. This is the literal "insufficient approval [authority]" case.
- **No approver at all:** an employee with no manager anywhere in their
  chain (e.g. a standalone hire, or an org-chart gap) would otherwise have a
  request that can *never* be legitimately decided. Since RBAC/admin roles
  don't exist until Phase 6, the interim rule is: if there is no manager or
  skip-level manager on record, **any active employee** may act as a
  fallback decider. This is a deliberate, documented gap — Phase 6 will
  narrow this to an `Admin`-role user instead of "anyone."

## Interim: identifying "who is approving" without auth (pre-Phase 6)

There is no authentication/session yet. Approve/reject/cancel calls take an
explicit `acting_manager_id` / `actor_employee_id` in the request body as a
stand-in for a real caller identity. **This is a known, temporary shape** —
Phase 6 will derive the acting identity from the JWT instead of a
client-supplied field, and these parameters will be removed from the
request schemas.

## Cross-year requests

A request is required to fall entirely within one calendar year
(`start_date.year == end_date.year`); a request spanning e.g. Dec 29 – Jan 3
is rejected at submission and the caller is told to split it into two.
Leave balances are tracked per-year, and splitting the request avoids ever
having to decide which year's balance a single row draws from.

## Day counting

`days_requested` counts **business days** (Mon-Fri) inclusive of both
endpoints — a Sat/Sun-only range is rejected as zero business days. No
public-holiday calendar is factored in; this is an explicit simplification
documented here rather than a bug. The same `count_business_days` helper
(`app/utils/dates.py`) is reused by the payroll integration below, so the
two numbers can never disagree.

## Payroll interaction

`LeaveService.get_unpaid_leave_days_for_period(employee_id, period_start,
period_end)` returns the business days of **approved `UNPAID`** leave that
overlap a given date range, clipping any request that straddles the range
boundary (e.g. leave running Jun 29 – Jul 2 contributes 2 days to June's
payroll period and 2 days to July's). This is the integration point the
Phase 4 payroll engine calls to compute the unpaid-leave deduction — no
separate "leave summary" table is needed; payroll reads directly from
`leave_requests`.
