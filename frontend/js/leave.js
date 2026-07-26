const Leave = (() => {
  let root = null;

  function canApprove() {
    return Store.isAdmin() || Store.isManager();
  }

  function adminOverrideHtml() {
    if (!Store.isAdmin()) return "";
    const options = Store.getEmployees()
      .slice()
      .sort((a, b) => a.name.localeCompare(b.name))
      .map(
        (e) =>
          `<option value="${e.id}" ${e.id === Store.getActingAsId() ? "selected" : ""}>${Dom.escapeHtml(e.name)}</option>`
      )
      .join("");
    return `
      <div class="card">
        <h3>Admin override</h3>
        <p class="muted small">
          As an Admin you can act on behalf of any employee below - submit,
          cancel, or view balances/requests/approvals as them. Leave unset
          to just browse read-only data like "who's on leave".
        </p>
        <div class="field">
          <label>Acting as</label>
          <select id="leave-admin-acting-as">
            <option value="">— none selected —</option>
            ${options}
          </select>
        </div>
      </div>
    `;
  }

  function html() {
    const today = new Date().toISOString().slice(0, 10);
    return `
      ${adminOverrideHtml()}

      <div class="grid-2">
        <div class="card">
          <h2>Submit leave request</h2>
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
          <h2>Leave balances</h2>
          <div id="leave-balances"></div>
        </div>
      </div>

      <div class="card">
        <div class="card-header"><h2>Leave requests</h2></div>
        <div id="leave-my-requests"></div>
      </div>

      ${
        canApprove()
          ? `<div class="card">
              <div class="card-header"><h2>Pending approvals</h2></div>
              <div id="leave-pending-approvals"></div>
            </div>`
          : ""
      }

      <div class="card">
        <div class="card-header">
          <h2>Who's on leave</h2>
          <div class="toolbar" style="margin:0;">
            <input type="date" id="leave-on-date" value="${today}" />
          </div>
        </div>
        <div id="leave-on-leave-list"></div>
      </div>

      ${
        Store.isAdmin()
          ? `<div class="card">
              <div class="card-header"><h2>Escalation sweep</h2></div>
              <p class="muted small">
                No scheduler is wired up yet (see docs/LEAVE.md) — run the sweep
                manually to flag pending requests older than the configured
                threshold so a skip-level manager can also act on them.
              </p>
              <button id="leave-escalate-btn" class="btn btn-secondary">Run escalation sweep now</button>
              <div id="leave-escalate-result" class="small muted" style="margin-top:8px;"></div>
            </div>`
          : ""
      }
    `;
  }

  function requireTarget(container, message) {
    const id = Store.effectiveEmployeeId();
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
    const employeeId = requireTarget(
      container,
      Store.isAdmin()
        ? "Select an employee above to view their balances."
        : "Your account isn't linked to an employee record - contact an admin."
    );
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
    const employeeId = requireTarget(
      container,
      Store.isAdmin()
        ? "Select an employee above to view their leave requests."
        : "Your account isn't linked to an employee record - contact an admin."
    );
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
    if (!canApprove()) return;
    const container = Dom.qs("#leave-pending-approvals", root);
    const managerId = requireTarget(
      container,
      "Select an employee above to view the requests they can approve."
    );
    if (!managerId) return;

    Dom.loading(container, "Loading pending approvals…");
    try {
      const { data } = await Api.leave.pendingApprovals(managerId);
      const tableHtml = requestsTableHtml(data, { showCancel: false, showDecision: true });
      container.innerHTML =
        tableHtml || `<div class="empty-state">No pending approvals right now.</div>`;
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

    const employeeId = Store.effectiveEmployeeId();
    if (!employeeId) {
      errorEl.textContent = Store.isAdmin()
        ? "Select an employee above first."
        : "Your account isn't linked to an employee record.";
      return;
    }

    const formData = new FormData(event.target);
    const payload = {
      leave_type: formData.get("leave_type"),
      start_date: formData.get("start_date"),
      end_date: formData.get("end_date"),
      reason: formData.get("reason") || undefined,
    };
    if (Store.isAdmin()) payload.employee_id = employeeId;

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
      const payload = Store.isAdmin() ? { actor_employee_id: Store.effectiveEmployeeId() } : {};
      await Api.leave.cancel(Number(btn.dataset.id), payload);
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
      const payload = Store.isAdmin()
        ? { acting_manager_id: Store.effectiveEmployeeId(), notes }
        : { notes };
      if (action === "approve") {
        await Api.leave.approve(id, payload);
      } else if (action === "reject") {
        await Api.leave.reject(id, payload);
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
    Dom.qs("#leave-on-date", root).addEventListener("change", refreshOnLeave);

    const pendingApprovalsEl = Dom.qs("#leave-pending-approvals", root);
    if (pendingApprovalsEl) pendingApprovalsEl.addEventListener("click", onPendingApprovalsClick);

    const escalateBtn = Dom.qs("#leave-escalate-btn", root);
    if (escalateBtn) escalateBtn.addEventListener("click", onEscalateClick);

    const adminSelect = Dom.qs("#leave-admin-acting-as", root);
    if (adminSelect) {
      adminSelect.addEventListener("change", (event) => {
        Store.setActingAs(event.target.value || null);
        refreshAll();
      });
    }

    await refreshAll();
  }

  return { render };
})();
