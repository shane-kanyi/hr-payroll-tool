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

function showLoginScreen() {
  document.getElementById("login-screen").hidden = false;
  document.getElementById("app-shell").hidden = true;
}

function showApp() {
  document.getElementById("login-screen").hidden = true;
  document.getElementById("app-shell").hidden = false;
}

function renderCurrentUserLabel() {
  const user = Store.getCurrentUser();
  const label = document.getElementById("current-user-label");
  if (!label || !user) return;
  const employeeName = user.employee ? ` — ${user.employee.name}` : "";
  label.textContent = `${user.email} (${Format.titleCase(user.role)}${employeeName})`;
}

async function loadInitialEmployees() {
  try {
    const { data } = await Api.employees.list({ per_page: 100 });
    Store.setEmployees(data);
  } catch (err) {
    console.error("Failed to load employees", err);
  }
}

function logout() {
  localStorage.removeItem("access_token");
  Store.clear();
  showLoginScreen();
}

async function bootApp() {
  showApp();
  renderCurrentUserLabel();

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

  await loadInitialEmployees();
  Nav.activate("overview");
}

async function tryResumeSession() {
  if (!localStorage.getItem("access_token")) {
    showLoginScreen();
    return;
  }
  try {
    const { data: user } = await Api.auth.me();
    Store.setCurrentUser(user);
    await bootApp();
  } catch (err) {
    logout();
  }
}

async function onLoginSubmit(event) {
  event.preventDefault();
  const errorEl = document.getElementById("login-error");
  errorEl.textContent = "";

  const formData = new FormData(event.target);
  try {
    const { data } = await Api.auth.login(formData.get("email"), formData.get("password"));
    localStorage.setItem("access_token", data.access_token);
    Store.setCurrentUser(data.user);
    event.target.reset();
    await bootApp();
  } catch (err) {
    errorEl.textContent = Dom.errorMessage(err);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("login-form").addEventListener("submit", onLoginSubmit);
  document.getElementById("logout-btn").addEventListener("click", logout);

  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => Nav.activate(btn.dataset.tab));
  });

  Store.subscribe(renderCurrentUserLabel);
  Api.onUnauthorized(() => {
    // A 401 mid-session (expired token, or the account was deactivated -
    // see user_lookup_loader in app/__init__.py) always bounces to login.
    logout();
  });

  tryResumeSession();
});
