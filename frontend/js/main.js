const Nav = (() => {
  const modules = { overview: Dashboard, employees: Employees, leave: Leave, payroll: Payroll };
  let current = "overview";

  function activate(tabId) {
    if (!modules[tabId]) return;
    current = tabId;

    document.querySelectorAll(".tab-btn").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.tab === tabId);
    });
    document.querySelectorAll(".tab-panel").forEach((panel) => {
      panel.classList.toggle("active", panel.id === `panel-${tabId}`);
    });

    const container = document.getElementById(`panel-${tabId}`);
    modules[tabId].render(container);
  }

  function rerenderCurrent() {
    activate(current);
  }

  return { activate, rerenderCurrent };
})();

function renderActingAsSelect(state) {
  const select = document.getElementById("acting-as-select");
  if (!select) return;

  const sorted = [...state.employees].sort((a, b) => a.name.localeCompare(b.name));
  select.innerHTML =
    `<option value="">— select an employee —</option>` +
    sorted
      .map(
        (e) =>
          `<option value="${e.id}" ${e.id === Number(state.actingAsId) ? "selected" : ""}>
            ${Dom.escapeHtml(e.name)} (${Dom.escapeHtml(e.role)})${e.is_active ? "" : " · inactive"}
          </option>`
      )
      .join("");
}

async function loadInitialEmployees() {
  try {
    const { data } = await Api.employees.list({ per_page: 100 });
    Store.setEmployees(data);
  } catch (err) {
    console.error("Failed to load employees for the acting-as selector", err);
  }
}

document.addEventListener("DOMContentLoaded", async () => {
  const statusEl = document.getElementById("api-status");
  try {
    const health = await Api.health();
    statusEl.textContent = `API ${health.status} · DB ${health.database}`;
    statusEl.className = "status-pill status-pill--ok";
  } catch (err) {
    statusEl.textContent = "API unreachable";
    statusEl.className = "status-pill status-pill--error";
    console.error(err);
  }

  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => Nav.activate(btn.dataset.tab));
  });

  document.getElementById("acting-as-select").addEventListener("change", (event) => {
    Store.setActingAs(event.target.value || null);
    Nav.rerenderCurrent();
  });

  Store.subscribe(renderActingAsSelect);

  await loadInitialEmployees();
  Nav.activate("overview");
});
