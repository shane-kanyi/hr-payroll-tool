const Payroll = (() => {
  let root = null;
  let selectedPeriodId = null;

  function adminHtml() {
    const now = new Date();
    return `
      <div class="grid-2">
        <div class="card">
          <h2>Generate payroll</h2>
          <form id="payroll-generate-form">
            <div class="form-grid">
              <div class="field">
                <label>Year</label>
                <input type="number" name="year" min="2000" max="2100" value="${now.getFullYear()}" required />
              </div>
              <div class="field">
                <label>Month</label>
                <select name="month">
                  ${Format.MONTH_NAMES.map(
                    (m, i) =>
                      `<option value="${i + 1}" ${i + 1 === now.getMonth() + 1 ? "selected" : ""}>${m}</option>`
                  ).join("")}
                </select>
              </div>
            </div>
            <div class="field-error" id="payroll-generate-error"></div>
            <button type="submit" class="btn btn-primary" style="margin-top:8px;">Generate / recompute</button>
          </form>
        </div>

        <div class="card">
          <h3>How this works</h3>
          <p class="muted small">
            Generating a period that's still in <strong>draft</strong>
            recomputes every entry from scratch — safe to re-run after a
            leave request gets approved. Once a period is
            <strong>finalized</strong>, it's locked: regenerating it is
            rejected, and its numbers are a permanent snapshot even if an
            employee's salary changes later. See docs/PAYROLL.md for the
            full formula.
          </p>
        </div>
      </div>

      <div class="card">
        <div class="card-header"><h2>Payroll periods</h2></div>
        <div id="payroll-periods-list"></div>
      </div>

      <div class="card" id="payroll-entries-card" hidden>
        <div class="card-header">
          <h2 id="payroll-entries-title">Entries</h2>
          <button id="payroll-finalize-btn" class="btn btn-success btn-sm" hidden type="button">
            Finalize this period
          </button>
        </div>
        <div id="payroll-entries-list"></div>
      </div>
    `;
  }

  function selfServiceHtml() {
    return `
      <div class="card">
        <div class="card-header"><h2>My payslips</h2></div>
        <p class="muted small">
          Payroll summaries and generation are Admin-only. Here's your own
          payslip history across every period you've been paid in.
        </p>
        <div id="payroll-my-entries"></div>
      </div>
    `;
  }

  function periodsTableHtml(periods) {
    if (periods.length === 0) {
      return `<div class="empty-state">No payroll periods generated yet.</div>`;
    }
    return `
      <div class="table-wrap">
        <table>
          <thead><tr><th>Period</th><th>Status</th><th>Entries</th><th>Generated</th><th>Finalized</th><th>Actions</th></tr></thead>
          <tbody>
            ${periods
              .map(
                (p) => `
                <tr>
                  <td>${Format.monthLabel(p.year, p.month)}</td>
                  <td><span class="${Format.statusBadgeClass(p.status)}">${p.status}</span></td>
                  <td>${p.entry_count}</td>
                  <td>${Format.dateTime(p.generated_at)}</td>
                  <td>${Format.dateTime(p.finalized_at)}</td>
                  <td><button class="btn btn-secondary btn-sm" data-action="view" data-id="${p.id}">View entries</button></td>
                </tr>`
              )
              .join("")}
          </tbody>
        </table>
      </div>
    `;
  }

  function taxBreakdownHtml(notes) {
    if (!notes) return "";
    const bands = (notes.tax_breakdown || [])
      .map(
        (b) => `
        <tr>
          <td>${b.band_lower} – ${b.band_upper ?? "∞"}</td>
          <td>${(b.rate * 100).toFixed(0)}%</td>
          <td>${Format.money(b.amount_taxed)}</td>
          <td>${Format.money(b.tax)}</td>
        </tr>`
      )
      .join("");

    return `
      <div class="calc-breakdown">
        <div>Employed ${notes.effective_start} → ${notes.effective_end}
          (proration factor ${Number(notes.proration_factor).toFixed(3)},
          ${notes.calendar_days_in_period} calendar days in period)</div>
        <div>Daily rate used for unpaid leave: ${Format.money(notes.daily_rate_for_leave)}
          (${notes.working_days_in_month} working days in month)</div>
        <div>Social security rate: ${(notes.social_security_rate * 100).toFixed(0)}%</div>
        <table style="margin-top:6px;">
          <thead><tr><th>Band</th><th>Rate</th><th>Taxed</th><th>Tax</th></tr></thead>
          <tbody>${bands || '<tr><td colspan="4">No tax owed on this band structure.</td></tr>'}</tbody>
        </table>
      </div>
    `;
  }

  function entriesTableHtml(entries, { showEmployee = true, showDetailsToggle = true } = {}) {
    if (entries.length === 0) {
      return `<div class="empty-state">No payroll entries here yet.</div>`;
    }
    return `
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              ${showEmployee ? "<th>Employee</th>" : "<th>Period</th>"}
              <th>Gross</th><th>Unpaid days</th><th>Unpaid ded.</th>
              <th>Taxable</th><th>Tax</th><th>Soc. security</th><th>Net</th><th></th>
            </tr>
          </thead>
          <tbody>
            ${entries
              .map(
                (e) => `
                <tr class="${showDetailsToggle ? "clickable" : ""}" data-action="toggle-details" data-id="${e.id}">
                  <td>${
                    showEmployee
                      ? Dom.escapeHtml(e.employee?.name || "—")
                      : `Period #${e.payroll_period_id}`
                  }</td>
                  <td>${Format.money(e.gross_salary)}</td>
                  <td>${Format.days(e.unpaid_leave_days)}</td>
                  <td>${Format.money(e.unpaid_leave_deduction)}</td>
                  <td>${Format.money(e.taxable_income)}</td>
                  <td>${Format.money(e.tax_deduction)}</td>
                  <td>${Format.money(e.social_security_deduction)}</td>
                  <td><strong>${Format.money(e.net_salary)}</strong></td>
                  <td><button class="btn btn-secondary btn-sm" type="button">Details</button></td>
                </tr>
                <tr class="details-row" data-details-for="${e.id}" hidden>
                  <td colspan="9">${taxBreakdownHtml(e.calculation_notes)}</td>
                </tr>`
              )
              .join("")}
          </tbody>
        </table>
      </div>
    `;
  }

  async function refreshPeriods() {
    const container = Dom.qs("#payroll-periods-list", root);
    Dom.loading(container, "Loading payroll periods…");
    try {
      const { data } = await Api.payroll.periods({ per_page: 50 });
      container.innerHTML = periodsTableHtml(data);
    } catch (err) {
      Dom.errorState(container, Dom.errorMessage(err));
    }
  }

  async function viewEntries(periodId) {
    selectedPeriodId = periodId;
    const card = Dom.qs("#payroll-entries-card", root);
    const list = Dom.qs("#payroll-entries-list", root);
    const title = Dom.qs("#payroll-entries-title", root);
    const finalizeBtn = Dom.qs("#payroll-finalize-btn", root);

    card.hidden = false;
    Dom.loading(list, "Loading entries…");

    try {
      const [{ data: period }, { data: entries }] = await Promise.all([
        Api.payroll.period(periodId),
        Api.payroll.entries(periodId),
      ]);
      title.textContent = `Entries — ${Format.monthLabel(period.year, period.month)} (${period.status})`;
      finalizeBtn.hidden = period.status !== "draft";
      finalizeBtn.dataset.id = periodId;
      list.innerHTML = entriesTableHtml(entries);
      card.scrollIntoView({ behavior: "smooth", block: "nearest" });
    } catch (err) {
      Dom.errorState(list, Dom.errorMessage(err));
    }
  }

  async function refreshMyEntries() {
    const container = Dom.qs("#payroll-my-entries", root);
    const employeeId = Store.getCurrentUser()?.employee?.id;
    if (!employeeId) {
      Dom.empty(container, "Your account isn't linked to an employee record - contact an admin.");
      return;
    }
    Dom.loading(container, "Loading your payslips…");
    try {
      const { data } = await Api.payroll.employeeEntries(employeeId);
      container.innerHTML = entriesTableHtml(data, { showEmployee: false });
    } catch (err) {
      Dom.errorState(container, Dom.errorMessage(err));
    }
  }

  async function onSubmitGenerate(event) {
    event.preventDefault();
    const errorEl = Dom.qs("#payroll-generate-error", root);
    errorEl.textContent = "";

    const formData = new FormData(event.target);
    const payload = {
      year: Number(formData.get("year")),
      month: Number(formData.get("month")),
    };

    try {
      const { data: period } = await Api.payroll.generate(payload);
      await refreshPeriods();
      await viewEntries(period.id);
    } catch (err) {
      errorEl.textContent = Dom.errorMessage(err);
    }
  }

  async function onPeriodsClick(event) {
    const btn = event.target.closest("button[data-action='view']");
    if (!btn) return;
    await viewEntries(Number(btn.dataset.id));
  }

  function onEntriesClick(event) {
    const row = event.target.closest("tr[data-action='toggle-details']");
    if (!row) return;
    const detailsRow = root.querySelector(`tr[data-details-for="${row.dataset.id}"]`);
    if (detailsRow) detailsRow.hidden = !detailsRow.hidden;
  }

  async function onFinalizeClick(event) {
    const id = Number(event.target.dataset.id);
    if (!id) return;
    if (!confirm("Finalize this payroll period? It can never be regenerated afterward.")) return;
    try {
      await Api.payroll.finalize(id);
      await refreshPeriods();
      await viewEntries(id);
    } catch (err) {
      alert(Dom.errorMessage(err));
    }
  }

  async function render(container) {
    root = container;

    if (!Store.isAdmin()) {
      root.innerHTML = selfServiceHtml();
      await refreshMyEntries();
      return;
    }

    root.innerHTML = adminHtml();
    Dom.qs("#payroll-generate-form", root).addEventListener("submit", onSubmitGenerate);
    Dom.qs("#payroll-periods-list", root).addEventListener("click", onPeriodsClick);
    Dom.qs("#payroll-entries-list", root).addEventListener("click", onEntriesClick);
    Dom.qs("#payroll-finalize-btn", root).addEventListener("click", onFinalizeClick);

    await refreshPeriods();
    if (selectedPeriodId) {
      await viewEntries(selectedPeriodId);
    }
  }

  return { render };
})();
