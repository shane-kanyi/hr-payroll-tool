const Dashboard = (() => {
  let root = null;

  function canApprove() {
    return Store.isAdmin() || Store.isManager();
  }

  function html() {
    return `
      <div class="stat-row" id="dash-stats"></div>

      <div class="grid-2">
        ${
          canApprove()
            ? `<div class="card">
                <div class="card-header">
                  <h2>Pending approvals</h2>
                  <button class="btn btn-secondary btn-sm" data-goto="leave">Go to Leave</button>
                </div>
                <div id="dash-pending"></div>
              </div>`
            : ""
        }

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
            <h2>${Store.isAdmin() ? "Recent payroll runs" : "My recent payslips"}</h2>
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
    let latestPeriodLabel = "Admin only";

    try {
      const { meta: employeeMeta } = await Api.employees.list({ is_active: true, per_page: 1 });
      activeCount = employeeMeta.total;
    } catch (err) {
      console.error(err);
    }

    if (Store.isAdmin()) {
      try {
        const { data: periods } = await Api.payroll.periods({ per_page: 1 });
        latestPeriodLabel =
          periods.length > 0
            ? `${Format.monthLabel(periods[0].year, periods[0].month)} (${periods[0].status})`
            : "None yet";
      } catch (err) {
        console.error(err);
      }
    }

    const tiles = [statTile(onLeaveCount, "People out today"), statTile(activeCount, "Active employees")];
    if (canApprove()) tiles.unshift(statTile(pendingCount, "Pending approvals for this user"));
    tiles.push(statTile(latestPeriodLabel, "Latest payroll period"));

    container.innerHTML = tiles.join("");
  }

  async function loadPending() {
    if (!canApprove()) return 0;
    const container = Dom.qs("#dash-pending", root);
    const managerId = Store.effectiveEmployeeId();
    if (!managerId) {
      Dom.empty(container, "Your account isn't linked to an employee record.");
      return 0;
    }
    Dom.loading(container, "Loading…");
    try {
      const { data } = await Api.leave.pendingApprovals(managerId);
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
    const employeeId = Store.getCurrentUser()?.employee?.id;
    if (!employeeId) {
      Dom.empty(container, "Your account isn't linked to an employee record.");
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

    if (!Store.isAdmin()) {
      const employeeId = Store.getCurrentUser()?.employee?.id;
      if (!employeeId) {
        Dom.empty(container, "Your account isn't linked to an employee record.");
        return;
      }
      try {
        const { data } = await Api.payroll.employeeEntries(employeeId);
        if (data.length === 0) {
          Dom.empty(container, "No payslips yet.");
          return;
        }
        container.innerHTML = `
          <div class="table-wrap">
            <table>
              <thead><tr><th>Net pay</th><th>Gross</th></tr></thead>
              <tbody>
                ${data
                  .slice(0, 3)
                  .map((e) => `<tr><td>${Format.money(e.net_salary)}</td><td>${Format.money(e.gross_salary)}</td></tr>`)
                  .join("")}
              </tbody>
            </table>
          </div>
        `;
      } catch (err) {
        Dom.errorState(container, Dom.errorMessage(err));
      }
      return;
    }

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
