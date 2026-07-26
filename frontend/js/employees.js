const Employees = (() => {
  let root = null;
  let teams = [];

  function html() {
    return `
      <div class="toolbar">
        <input id="emp-search" placeholder="Search by name…" />
        <select id="emp-filter-active">
          <option value="">All statuses</option>
          <option value="true">Active only</option>
          <option value="false">Inactive only</option>
        </select>
        <select id="emp-filter-team"><option value="">All teams</option></select>
        ${
          Store.isAdmin()
            ? '<button id="emp-new-btn" class="btn btn-primary" type="button">+ New employee</button>'
            : ""
        }
      </div>

      <div id="emp-form-panel" class="card" hidden></div>

      <div class="card">
        <div class="card-header"><h2>Employees</h2></div>
        <div id="emp-table-wrap"></div>
      </div>

      <div class="card">
        <div class="card-header">
          <h2>Org chart</h2>
          <label class="small"><input type="checkbox" id="emp-org-include-inactive" /> include inactive</label>
        </div>
        <div id="emp-org-chart"></div>
      </div>
    `;
  }

  function employeeFormHtml(employee = null) {
    const opts = (list, valueKey, labelFn, selected) =>
      list
        .map(
          (item) =>
            `<option value="${item[valueKey]}" ${item[valueKey] === selected ? "selected" : ""}>${Dom.escapeHtml(
              labelFn(item)
            )}</option>`
        )
        .join("");

    const activeEmployees = Store.getEmployees().filter((e) => e.is_active && e.id !== employee?.id);

    return `
      <h2>${employee ? "Edit employee" : "New employee"}</h2>
      <form id="emp-form">
        <div class="form-grid">
          <div class="field">
            <label>Name</label>
            <input name="name" required maxlength="150" value="${Dom.escapeHtml(employee?.name || "")}" />
          </div>
          <div class="field">
            <label>Role / title</label>
            <input name="role" required maxlength="120" value="${Dom.escapeHtml(employee?.role || "")}" />
          </div>
          <div class="field">
            <label>Team</label>
            <select name="team_id">
              <option value="">No team</option>
              ${opts(teams, "id", (t) => t.name, employee?.team?.id)}
            </select>
          </div>
          <div class="field">
            <label>Manager</label>
            <select name="manager_id">
              <option value="">No manager</option>
              ${opts(activeEmployees, "id", (e) => `${e.name} (${e.role})`, employee?.manager?.id)}
            </select>
          </div>
          <div class="field">
            <label>Start date</label>
            <input type="date" name="start_date" required value="${employee?.start_date || ""}" />
          </div>
          <div class="field">
            <label>Monthly salary</label>
            <input type="number" name="salary" min="0" step="0.01" required value="${employee?.salary || ""}" />
          </div>
          <div class="field">
            <label>Employment type</label>
            <select name="employment_type">
              ${["full_time", "part_time", "contract"]
                .map(
                  (t) =>
                    `<option value="${t}" ${t === employee?.employment_type ? "selected" : ""}>${Format.titleCase(t)}</option>`
                )
                .join("")}
            </select>
          </div>
        </div>
        <div class="field-error" id="emp-form-error"></div>
        <div class="actions" style="margin-top: 8px;">
          <button type="submit" class="btn btn-primary">${employee ? "Save changes" : "Create employee"}</button>
          <button type="button" class="btn btn-secondary" id="emp-form-cancel">Cancel</button>
        </div>
      </form>
    `;
  }

  function statusBadge(employee) {
    return employee.is_active
      ? '<span class="badge badge-active">Active</span>'
      : '<span class="badge badge-inactive">Inactive</span>';
  }

  function tableHtml(employees) {
    if (employees.length === 0) {
      return `<div class="empty-state">No employees match these filters yet.</div>`;
    }
    const rows = employees
      .map(
        (e) => `
        <tr>
          <td>${Dom.escapeHtml(e.name)}</td>
          <td>${Dom.escapeHtml(e.role)}</td>
          <td>${Dom.escapeHtml(e.team?.name || "—")}</td>
          <td>${Dom.escapeHtml(e.manager?.name || "—")}</td>
          <td>${Format.date(e.start_date)}</td>
          <td>${Format.money(e.salary)}</td>
          <td>${Format.titleCase(e.employment_type)}</td>
          <td>${statusBadge(e)}</td>
          <td class="actions">
            ${
              !Store.isAdmin()
                ? ""
                : e.is_active
                  ? `<button class="btn btn-danger btn-sm" data-action="deactivate" data-id="${e.id}">Deactivate</button>`
                  : `<button class="btn btn-success btn-sm" data-action="reactivate" data-id="${e.id}">Reactivate</button>`
            }
          </td>
        </tr>`
      )
      .join("");

    return `
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Name</th><th>Role</th><th>Team</th><th>Manager</th>
              <th>Start date</th><th>Salary</th><th>Type</th><th>Status</th><th>Actions</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    `;
  }

  function orgNodeHtml(node) {
    const children = node.children?.length
      ? `<ul>${node.children.map(orgNodeHtml).join("")}</ul>`
      : "";
    return `
      <li>
        <div class="tree-node">
          <strong>${Dom.escapeHtml(node.name)}</strong>
          <span class="role">${Dom.escapeHtml(node.role)}${node.team ? " · " + Dom.escapeHtml(node.team) : ""}</span>
          ${!node.is_active ? '<span class="badge badge-inactive">Inactive</span>' : ""}
        </div>
        ${children}
      </li>
    `;
  }

  async function refreshTable() {
    const wrap = Dom.qs("#emp-table-wrap", root);
    Dom.loading(wrap, "Loading employees…");
    const params = {
      search: Dom.qs("#emp-search", root).value || undefined,
      is_active: Dom.qs("#emp-filter-active", root).value || undefined,
      team_id: Dom.qs("#emp-filter-team", root).value || undefined,
      per_page: 100,
    };
    try {
      const { data } = await Api.employees.list(params);
      wrap.innerHTML = tableHtml(data);
    } catch (err) {
      Dom.errorState(wrap, Dom.errorMessage(err));
    }
  }

  async function refreshOrgChart() {
    const container = Dom.qs("#emp-org-chart", root);
    Dom.loading(container, "Loading org chart…");
    const includeInactive = Dom.qs("#emp-org-include-inactive", root).checked;
    try {
      const { data } = await Api.employees.orgChart(includeInactive);
      if (data.length === 0) {
        Dom.empty(container, "No employees yet.");
        return;
      }
      container.innerHTML = `<div class="tree"><ul>${data.map(orgNodeHtml).join("")}</ul></div>`;
    } catch (err) {
      Dom.errorState(container, Dom.errorMessage(err));
    }
  }

  async function refreshAll() {
    await Promise.all([refreshTable(), refreshOrgChart(), refreshEmployeeCache()]);
  }

  async function refreshEmployeeCache() {
    try {
      const { data } = await Api.employees.list({ per_page: 100 });
      Store.setEmployees(data);
    } catch (err) {
      // Non-fatal for the tab itself; dropdowns elsewhere just stay stale.
      console.error("Failed to refresh employee cache", err);
    }
  }

  function openForm() {
    const panel = Dom.qs("#emp-form-panel", root);
    panel.hidden = false;
    panel.innerHTML = employeeFormHtml();
    Dom.qs("#emp-form", panel).addEventListener("submit", onSubmitForm);
    Dom.qs("#emp-form-cancel", panel).addEventListener("click", closeForm);
  }

  function closeForm() {
    const panel = Dom.qs("#emp-form-panel", root);
    panel.hidden = true;
    panel.innerHTML = "";
  }

  async function onSubmitForm(event) {
    event.preventDefault();
    const form = event.target;
    const errorEl = Dom.qs("#emp-form-error", form);
    errorEl.textContent = "";

    const formData = new FormData(form);
    const payload = {
      name: formData.get("name"),
      role: formData.get("role"),
      team_id: formData.get("team_id") || null,
      manager_id: formData.get("manager_id") || null,
      start_date: formData.get("start_date"),
      salary: formData.get("salary"),
      employment_type: formData.get("employment_type"),
    };

    try {
      await Api.employees.create(payload);
      closeForm();
      await refreshAll();
    } catch (err) {
      errorEl.textContent = Dom.errorMessage(err);
    }
  }

  async function onTableClick(event) {
    const btn = event.target.closest("button[data-action]");
    if (!btn) return;
    const id = Number(btn.dataset.id);
    const action = btn.dataset.action;

    try {
      if (action === "deactivate") {
        if (!confirm("Deactivate this employee? Payroll history is preserved.")) return;
        await Api.employees.deactivate(id);
      } else if (action === "reactivate") {
        await Api.employees.reactivate(id);
      }
      await refreshAll();
    } catch (err) {
      alert(Dom.errorMessage(err));
    }
  }

  async function loadTeams() {
    const { data } = await Api.teams.list();
    teams = data;
    const teamSelect = Dom.qs("#emp-filter-team", root);
    teamSelect.innerHTML =
      `<option value="">All teams</option>` +
      teams.map((t) => `<option value="${t.id}">${Dom.escapeHtml(t.name)}</option>`).join("");
  }

  async function render(container) {
    root = container;
    root.innerHTML = html();

    const newBtn = Dom.qs("#emp-new-btn", root);
    if (newBtn) newBtn.addEventListener("click", openForm);
    Dom.qs("#emp-search", root).addEventListener("input", debounce(refreshTable, 300));
    Dom.qs("#emp-filter-active", root).addEventListener("change", refreshTable);
    Dom.qs("#emp-filter-team", root).addEventListener("change", refreshTable);
    Dom.qs("#emp-org-include-inactive", root).addEventListener("change", refreshOrgChart);
    Dom.qs("#emp-table-wrap", root).addEventListener("click", onTableClick);

    await loadTeams();
    await refreshAll();
  }

  function debounce(fn, delay) {
    let timer;
    return (...args) => {
      clearTimeout(timer);
      timer = setTimeout(() => fn(...args), delay);
    };
  }

  return { render };
})();
