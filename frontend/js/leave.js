const Leave = (() => {
  let root = null;

  function html() {
    const today = new Date().toISOString().slice(0, 10);
    return `
      <div class="grid-2">
        <div class="card">
          <h2>Submit leave request</h2>
          <div id="leave-submit-identity-warning"></div>
          <form id="leave-submit-form">
            <div class="form-grid">
              <div class="field">
                <label>Leave type</label>
                <select name="leave_type">
                  <option value="annual">Annual</option>
                  <option value="sick">Sick</option>
                  <option value="unpaid">Unpaid</option>
                </select>
              </div>
              <div class="field">
                <label>Start date</label>
                <input type="date" name="start_date" required />
              </div>
              <div class="field">
                <label>End date</label>
                <input type="date" name="end_date" required />
              </div>
            </div>
            <div class="field" style="margin-top:8px;">
              <label>Reason (optional)</label>
              <textarea name="reason" maxlength="2000"></textarea>
            </div>
            <div class="field-error" id="leave-submit-error"></div>
            <button type="submit" class="btn btn-primary" style="margin-top:8px;">Submit request</button>
          </form>
        </div>

        <div class="card">
          <h2>My leave balances</h2>
          <div id="leave-balances"></div>
        </div>
      </div>

      <div class="card">
        <div class="card-header"><h2>My leave requests</h2></div>
        <div id="leave-my-requests"></div>
      </div>

      <div class="card">
        <div class="card-header"><h2>Pending approvals</h2></div>
        <div id="leave-pending-approvals"></div>
      </div>

      <div class="card">
        <div class="card-header">
          <h2>Who's on leave</h2>
          <div class="toolbar" style="margin:0;">
            <input type="date" id="leave-on-date" value="${today}" />
          </div>
        </div>
        <div id="leave-on-leave-list"></div>
      </div>

      <div class="card">
        <div class="card-header"><h2>Escalation sweep</h2></div>
        <p class="muted small">
          No scheduler is wired up yet (see docs/LEAVE.md) — run the sweep
          manually to flag pending requests older than the configured
          threshold so a skip-level manager can also act on them.
        </p>
        <button id="leave-escalate-btn" class="btn btn-secondary">Run escalation sweep now</button>
        <div id="leave-escalate-result" class="small muted" style="margin-top:8px;"></div>
      </div>
    `;
  }

  function requireActingAs(container, message) {
    const id = Store.getActingAsId();
    if (!id) {
      Dom.empty(container, message);
      return null;
    }
    return id;
  }

  function requestRow(request, { showCancel, showDecision }) {
    const badge = `<span class="${Format.statusBadgeClass(request.status)}">${request.status}</span>`;
    const escalated = request.escalated_at
      ? '<span class="badge badge-escalated">Escalated</span>'
      : "";
    const actions = [];
    if (showCancel && request.status === "pending") {
      actions.push(`<button class="btn btn-secondary btn-sm" data-action="cancel" data-id="${request.id}">Cancel</button>`);
    }
    if (showDecision && request.status === "pending") {
      actions.push(`<button class="btn btn-success btn-sm" data-action="approve" data-id="${request.id}">Approve</button>`);
      actions.push(`<button class="btn btn-danger btn-sm" data-action="reject" data-id="${request.id}">Reject</button>`);
    }
    return `
      <tr>
        <td>${Dom.escapeHtml(request.employee?.name || "—")}</td>
        <td>${Format.titleCase(request.leave_type)}</td>
        <td>${Format.date(request.start_date)} → ${Format.date(request.end_date)}</td>
        <td>${Format.days(request.days_requested)}</td>
        <td>${badge} ${escalated}</td>
        <td class="actions">${actions.join("")}</td>
      </tr>
    `;
  }

  function requestsTableHtml(requests, opts) {
    if (requests.length === 0) return null;
    return `
      <div class="table-wrap">
        <table>
          <thead><tr><th>Employee</th><th>Type</th><th>Dates</th><th>Days</th><th>Status</th><th>Actions</th></tr></thead>
          <tbody>${requests.map((r) => requestRow(r, opts)).join("")}</tbody>
        </table>
      </div>
    `;
  }

  async function refreshBalances() {
    const container = Dom.qs("#leave-balances", root);
    const employeeId = requireActingAs(container, "Select an employee in the header to see their leave balances.");
    if (!employeeId) return;

    Dom.loading(container, "Loading balances…");
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
                <div class="stat-label">${Format.titleCase(b.leave_type)} remaining (${b.used_days}/${b.allocated_days} used)</div>
              </div>`
            )
            .join("")}
        </div>
      `;
    } catch (err) {
      Dom.errorState(container, Dom.errorMessage(err));
    }
  }

  async function refreshMyRequests() {
    const container = Dom.qs("#leave-my-requests", root);
    const employeeId = requireActingAs(container, "Select an employee in the header to see their requests.");
    if (!employeeId) return;

    Dom.loading(container, "Loading requests…");
    try {
      const { data } = await Api.leave.list({ employee_id: employeeId, per_page: 50 });
      const tableHtml = requestsTableHtml(data, { showCancel: true, showDecision: false });
      container.innerHTML = tableHtml || `<div class="empty-state">No leave requests submitted yet.</div>`;
    } catch (err) {
      Dom.errorState(container, Dom.errorMessage(err));
    }
  }

  async function refreshPendingApprovals() {
    const container = Dom.qs("#leave-pending-approvals", root);
    const employeeId = requireActingAs(container, "Select an employee in the header to see requests they can approve.");
    if (!employeeId) return;

    Dom.loading(container, "Loading pending approvals…");
    try {
      const { data } = await Api.leave.pendingApprovals(employeeId);
      const tableHtml = requestsTableHtml(data, { showCancel: false, showDecision: true });
      container.innerHTML =
        tableHtml || `<div class="empty-state">No pending approvals for this employee right now.</div>`;
    } catch (err) {
      Dom.errorState(container, Dom.errorMessage(err));
    }
  }

  async function refreshOnLeave() {
    const container = Dom.qs("#leave-on-leave-list", root);
    const onDate = Dom.qs("#leave-on-date", root).value;
    Dom.loading(container, "Loading…");
    try {
      const { data } = await Api.leave.onLeave(onDate);
      if (data.length === 0) {
        Dom.empty(container, "Nobody is on approved leave for this date.");
        return;
      }
      container.innerHTML = `
        <div class="table-wrap">
          <table>
            <thead><tr><th>Employee</th><th>Type</th><th>Dates</th></tr></thead>
            <tbody>
              ${data
                .map(
                  (r) => `
                  <tr>
                    <td>${Dom.escapeHtml(r.employee?.name || "—")}</td>
                    <td>${Format.titleCase(r.leave_type)}</td>
                    <td>${Format.date(r.start_date)} → ${Format.date(r.end_date)}</td>
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

  async function refreshAll() {
    await Promise.all([
      refreshBalances(),
      refreshMyRequests(),
      refreshPendingApprovals(),
      refreshOnLeave(),
    ]);
  }

  async function onSubmitForm(event) {
    event.preventDefault();
    const errorEl = Dom.qs("#leave-submit-error", root);
    errorEl.textContent = "";

    const employeeId = Store.getActingAsId();
    if (!employeeId) {
      errorEl.textContent = "Select an employee in the header first.";
      return;
    }

    const formData = new FormData(event.target);
    const payload = {
      employee_id: employeeId,
      leave_type: formData.get("leave_type"),
      start_date: formData.get("start_date"),
      end_date: formData.get("end_date"),
      reason: formData.get("reason") || undefined,
    };

    try {
      await Api.leave.submit(payload);
      event.target.reset();
      await Promise.all([refreshMyRequests(), refreshBalances(), refreshOnLeave()]);
    } catch (err) {
      errorEl.textContent = Dom.errorMessage(err);
    }
  }

  async function onMyRequestsClick(event) {
    const btn = event.target.closest("button[data-action='cancel']");
    if (!btn) return;
    if (!confirm("Cancel this leave request?")) return;
    try {
      await Api.leave.cancel(Number(btn.dataset.id), { actor_employee_id: Store.getActingAsId() });
      await Promise.all([refreshMyRequests(), refreshBalances()]);
    } catch (err) {
      alert(Dom.errorMessage(err));
    }
  }

  async function onPendingApprovalsClick(event) {
    const btn = event.target.closest("button[data-action]");
    if (!btn) return;
    const id = Number(btn.dataset.id);
    const action = btn.dataset.action;
    const notes = prompt(`Optional note for this ${action}:`) || undefined;

    try {
      const actingManagerId = Store.getActingAsId();
      if (action === "approve") {
        await Api.leave.approve(id, { acting_manager_id: actingManagerId, notes });
      } else if (action === "reject") {
        await Api.leave.reject(id, { acting_manager_id: actingManagerId, notes });
      }
      await Promise.all([refreshPendingApprovals(), refreshOnLeave()]);
    } catch (err) {
      alert(Dom.errorMessage(err));
    }
  }

  async function onEscalateClick() {
    const resultEl = Dom.qs("#leave-escalate-result", root);
    resultEl.textContent = "Running…";
    try {
      const { meta } = await Api.leave.escalate();
      resultEl.textContent = `${meta.escalated_count} request(s) newly escalated.`;
      await refreshPendingApprovals();
    } catch (err) {
      resultEl.textContent = Dom.errorMessage(err);
    }
  }

  async function render(container) {
    root = container;
    root.innerHTML = html();

    Dom.qs("#leave-submit-form", root).addEventListener("submit", onSubmitForm);
    Dom.qs("#leave-my-requests", root).addEventListener("click", onMyRequestsClick);
    Dom.qs("#leave-pending-approvals", root).addEventListener("click", onPendingApprovalsClick);
    Dom.qs("#leave-on-date", root).addEventListener("change", refreshOnLeave);
    Dom.qs("#leave-escalate-btn", root).addEventListener("click", onEscalateClick);

    await refreshAll();
  }

  return { render };
})();
