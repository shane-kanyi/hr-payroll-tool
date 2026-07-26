const Dashboard = (() => {
  let root = null;

  function html() {
    return `
      <div class="stat-row" id="dash-stats"></div>

      <div class="grid-2">
        <div class="card">
          <div class="card-header">
            <h2>Pending approvals</h2>
            <button class="btn btn-secondary btn-sm" data-goto="leave">Go to Leave</button>
          </div>
          <div id="dash-pending"></div>
        </div>

        <div class="card">
          <div class="card-header">
            <h2>Who's out today</h2>
            <button class="btn btn-secondary btn-sm" data-goto="leave">Go to Leave</button>
          </div>
          <div id="dash-onleave"></div>
        </div>
      </div>

      <div class="grid-2">
        <div class="card">
          <div class="card-header">
            <h2>My leave balances</h2>
            <button class="btn btn-secondary btn-sm" data-goto="leave">Go to Leave</button>
          </div>
          <div id="dash-balances"></div>
        </div>

        <div class="card">
          <div class="card-header">
            <h2>Recent payroll runs</h2>
            <button class="btn btn-secondary btn-sm" data-goto="payroll">Go to Payroll</button>
          </div>
          <div id="dash-payroll"></div>
        </div>
      </div>
    `;
  }

  function statTile(value, label) {
    return `<div class="stat-tile"><div class="stat-value">${value}</div><div class="stat-label">${label}</div></div>`;
  }

  async function loadStats(pendingCount, onLeaveCount) {
    const container = Dom.qs("#dash-stats", root);
    let activeCount = "—";
    let latestPeriodLabel = "None yet";
    try {
      const [{ meta: employeeMeta }, { data: periods }] = await Promise.all([
        Api.employees.list({ is_active: true, per_page: 1 }),
        Api.payroll.periods({ per_page: 1 }),
      ]);
      activeCount = employeeMeta.total;
      if (periods.length > 0) {
        const latest = periods[0];
        latestPeriodLabel = `${Format.monthLabel(latest.year, latest.month)} (${latest.status})`;
      }
    } catch (err) {
      console.error(err);
    }

    container.innerHTML = [
      statTile(pendingCount, "Pending approvals for this user"),
      statTile(onLeaveCount, "People out today"),
      statTile(activeCount, "Active employees"),
      statTile(latestPeriodLabel, "Latest payroll period"),
    ].join("");
  }

  async function loadPending() {
    const container = Dom.qs("#dash-pending", root);
    const employeeId = Store.getActingAsId();
    if (!employeeId) {
      Dom.empty(container, "Select an employee in the header to see their pending approvals.");
      return 0;
    }
    Dom.loading(container, "Loading…");
    try {
      const { data } = await Api.leave.pendingApprovals(employeeId);
      if (data.length === 0) {
        Dom.empty(container, "No pending approvals right now.");
        return 0;
      }
      container.innerHTML = `
        <div class="table-wrap">
          <table>
            <thead><tr><th>Employee</th><th>Type</th><th>Dates</th><th>Status</th></tr></thead>
            <tbody>
              ${data
                .slice(0, 5)
                .map(
                  (r) => `
                  <tr>
                    <td>${Dom.escapeHtml(r.employee?.name || "—")}</td>
                    <td>${Format.titleCase(r.leave_type)}</td>
                    <td>${Format.date(r.start_date)} → ${Format.date(r.end_date)}</td>
                    <td>${r.escalated_at ? '<span class="badge badge-escalated">Escalated</span>' : '<span class="badge badge-pending">Pending</span>'}</td>
                  </tr>`
                )
                .join("")}
            </tbody>
          </table>
        </div>
      `;
      return data.length;
    } catch (err) {
      Dom.errorState(container, Dom.errorMessage(err));
      return 0;
    }
  }

  async function loadOnLeave() {
    const container = Dom.qs("#dash-onleave", root);
    Dom.loading(container, "Loading…");
    try {
      const today = new Date().toISOString().slice(0, 10);
      const { data } = await Api.leave.onLeave(today);
      if (data.length === 0) {
        Dom.empty(container, "Nobody is on approved leave today.");
        return 0;
      }
      container.innerHTML = `
        <ul class="small">
          ${data
            .slice(0, 8)
            .map(
              (r) =>
                `<li>${Dom.escapeHtml(r.employee?.name || "—")} — ${Format.titleCase(r.leave_type)} (until ${Format.date(r.end_date)})</li>`
            )
            .join("")}
        </ul>
      `;
      return data.length;
    } catch (err) {
      Dom.errorState(container, Dom.errorMessage(err));
      return 0;
    }
  }

  async function loadBalances() {
    const container = Dom.qs("#dash-balances", root);
    const employeeId = Store.getActingAsId();
    if (!employeeId) {
      Dom.empty(container, "Select an employee in the header to see their balances.");
      return;
    }
    Dom.loading(container, "Loading…");
    try {
      const { data } = await Api.leave.balances(employeeId, new Date().getFullYear());
      if (data.length === 0) {
        Dom.empty(container, "No leave balances for this year yet.");
        return;
      }
      container.innerHTML = `
        <div class="stat-row" style="margin-bottom:0;">
          ${data
            .map(
              (b) => `
              <div class="stat-tile">
                <div class="stat-value">${Format.days(b.remaining_days)}</div>
                <div class="stat-label">${Format.titleCase(b.leave_type)} remaining</div>
              </div>`
            )
            .join("")}
        </div>
      `;
    } catch (err) {
      Dom.errorState(container, Dom.errorMessage(err));
    }
  }

  async function loadRecentPayroll() {
    const container = Dom.qs("#dash-payroll", root);
    Dom.loading(container, "Loading…");
    try {
      const { data } = await Api.payroll.periods({ per_page: 3 });
      if (data.length === 0) {
        Dom.empty(container, "No payroll periods generated yet.");
        return;
      }
      container.innerHTML = `
        <div class="table-wrap">
          <table>
            <thead><tr><th>Period</th><th>Status</th><th>Entries</th></tr></thead>
            <tbody>
              ${data
                .map(
                  (p) => `
                  <tr>
                    <td>${Format.monthLabel(p.year, p.month)}</td>
                    <td><span class="${Format.statusBadgeClass(p.status)}">${p.status}</span></td>
                    <td>${p.entry_count}</td>
                  </tr>`
                )
                .join("")}
            </tbody>
          </table>
        </div>
      `;
    } catch (err) {
      Dom.errorState(container, Dom.errorMessage(err));
    }
  }

  function wireGotoButtons() {
    root.querySelectorAll("[data-goto]").forEach((btn) => {
      btn.addEventListener("click", () => Nav.activate(btn.dataset.goto));
    });
  }

  async function render(container) {
    root = container;
    root.innerHTML = html();
    wireGotoButtons();

    const [pendingCount, onLeaveCount] = await Promise.all([loadPending(), loadOnLeave()]);
    await Promise.all([loadStats(pendingCount, onLeaveCount), loadBalances(), loadRecentPayroll()]);
  }

  return { render };
})();
