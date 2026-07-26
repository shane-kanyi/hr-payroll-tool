# Payroll: Formula & Assumptions

This documents the exact calculation `PayrollService._calculate_entry`
performs — a simple tax-bracket-plus-flat-social-security scheme, chosen
deliberately over trying to match any real country's tax code exactly (see
"Tax: simple progressive brackets" below for why).

## Pipeline, in order

```
gross_salary            = employee.salary * proration_factor
unpaid_leave_deduction  = min(daily_rate_for_leave * unpaid_leave_days, gross_salary)
taxable_income          = gross_salary - unpaid_leave_deduction
tax_deduction           = progressive_tax(taxable_income)
social_security_deduction = taxable_income * SOCIAL_SECURITY_RATE
net_salary              = taxable_income - tax_deduction - social_security_deduction
```

Every intermediate value is stored on the `PayrollEntry` row, not just the
final net figure — a payslip should be able to show its work, and an
auditor should never have to recompute `taxable_income` by hand from
`gross_salary` and `unpaid_leave_deduction` to check it.

## Column semantics (why `gross_salary` isn't just `employee.salary`)

`gross_salary` on the entry is the employee's contractual monthly salary
**prorated for the days they were actually employed during the period**
(see "Proration" below) — it does *not* yet reflect unpaid leave.
`taxable_income` is `gross_salary` minus the unpaid-leave deduction — the
amount that's actually subject to tax and social security. Keeping these
as two separate stored columns (rather than folding unpaid leave into
`gross_salary` directly) means a payslip can show "you were paid for N of
M days this month" and "of that, X days were unpaid leave" as distinct,
auditable line items instead of a single opaque number.

## Proration (mid-month joiners and exits)

```
effective_start = max(period_start, employee.start_date)
effective_end   = period_end, or the employee's deactivation date if they
                  were deactivated before the period ended
proration_factor = days_employed / calendar_days_in_period   (capped at 1.0)
```

This uses **calendar days**, not working days — a flat monthly salary is
conventionally treated as covering every calendar day of the month, so a
daily rate for proration purposes is `salary / days_in_month`. An employee
not employed on *any* day of the period (hired after it ends, or
deactivated before it begins) gets no `PayrollEntry` for that period at
all, rather than a zero-value row — the entries table only contains people
who were actually owed something.

This proration is applied **symmetrically** to joiners and to employees
deactivated partway through the period — leaving exits unprorated would
silently overpay anyone deactivated mid-month, so the same formula covers
both without extra branching. A known gap: this uses `deactivated_at` as a
proxy for "last worked day," which conflates "when HR clicked deactivate"
with "when the person's employment actually ended." A real system would
want a distinct `termination_date` field; documented here rather than
silently assumed away.

## Unpaid leave deduction (a different day-count basis, deliberately)

```
daily_rate_for_leave = employee.salary / working_days_in_month   (business days, Mon-Fri)
unpaid_leave_deduction = daily_rate_for_leave * unpaid_leave_days
```

Note this uses **working days**, not calendar days — the opposite
denominator from the proration calculation above. This is intentional and
mirrors common real-world payroll practice: a monthly salary "covers" every
calendar day (weekends included) when someone joins or leaves, but a day of
*unpaid leave* is only meaningful on a day the person would otherwise have
worked, so its cost is measured against working days. `unpaid_leave_days`
itself comes from `LeaveService.get_unpaid_leave_days_for_period`, which
counts business days of **approved** `UNPAID` leave overlapping
the period, clipped to the period boundary — so a leave request spanning a
period boundary (e.g. Jun 29 - Jul 2) is split correctly between June's and
July's payroll runs.

The deduction is capped at `gross_salary` so a data inconsistency (e.g. an
unpaid-leave request predating the employee's `start_date`, which the leave
engine doesn't currently forbid) can't push a payslip negative before tax.

## Tax: simple progressive brackets

Defined in `app/utils/tax.py`, applied to **monthly** `taxable_income`:

| Band | Rate |
|---|---|
| 0 – 1,000 | 0% |
| 1,000 – 3,000 | 10% |
| 3,000 – 6,000 | 20% |
| 6,000+ | 25% |

This is a **marginal** (bracket-by-bracket) calculation, not "look up the
top rate for this income and apply it to the whole amount" — only the
slice of income inside each band is taxed at that band's rate. This is
what avoids the classic "boundary cliff" bug: at a naive flat-rate scheme,
earning $1 more and crossing from the 10% band into the 20% band would make
you *worse off* than staying just under the line. With marginal brackets,
crossing $3,000 by one dollar costs you 20 cents of extra tax, not hundreds
of dollars. See `tests/test_tax.py::test_no_cliff_at_bracket_boundary` and
`tests/test_payroll_service.py::test_salary_near_tax_bracket_boundary_no_cliff`.

These bracket values are illustrative constants, chosen to make the
marginal-vs-cliff behavior easy to verify in tests with clean numbers —
they're not meant to correspond to any real country's tax code.

## Social security: flat rate

`social_security_deduction = taxable_income * SOCIAL_SECURITY_RATE`
(config, default `0.06` / 6%). Flat percentage of the same `taxable_income`
base used for tax — no minimum floor, no contribution ceiling. A real
scheme would likely cap contributions above some income level; omitted
here as an explicit simplification, not an oversight.

## Edge cases and how each is handled

- **Mid-month joiners**: `proration_factor` above.
- **Zero-deduction cases**: an employee earning $0 (allowed by the
  `salary >= 0` constraint), or one whose entire month is unpaid leave,
  correctly nets out to `taxable_income = 0` and therefore `tax = 0`,
  `social_security = 0`, `net = 0` — no special-casing needed, it falls out
  of the formula naturally.
- **Salary near a bracket boundary**: handled by the marginal tax
  calculation, not a special case — see above.
- **Inactive employees**: excluded entirely if they were deactivated
  *before* the period started (they weren't employed at all during it);
  prorated (not excluded) if deactivated *during* the period, since they
  were owed partial pay for the days they did work; currently-active
  employees are of course always included in full for periods they were
  employed during.
- **Partial unpaid leave**: any number of business days up to the whole
  period; the deduction scales linearly and is capped at `gross_salary`
  (see above).

## Snapshots: why payroll is never recalculated after finalization

`PayrollPeriod.status` moves `draft -> finalized` one-way.
`generate_payroll` recomputes and replaces every entry for a period **only
while it's still `draft`** (this is a deliberate "preview" workflow — HR
can generate early, let leave approvals catch up, and re-run before
finalizing). Once `finalized`, `generate_payroll` refuses to touch that
period again (`ConflictError`), and every numeric column on `PayrollEntry`
is a stored snapshot — if an employee's salary changes afterward, already-
finalized payslips are provably unaffected (see
`test_finalized_payroll_is_never_recalculated_even_if_salary_changes_later`).
This is what "payroll history must remain intact" means in practice: not
just "don't delete the row," but "the numbers on it can never silently
drift out from under a past pay period."
