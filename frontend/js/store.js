const Store = (() => {
  const ACTING_AS_KEY = "hr_acting_as_employee_id";

  const state = {
    currentUser: null, // { id, email, role, employee: {id, name} | null }
    // Admin-only override: lets an Admin preview/act as a specific
    // employee (e.g. to approve on their behalf) without logging out.
    // Non-admins never see or use this.
    actingAsId: localStorage.getItem(ACTING_AS_KEY) || null,
    employees: [],
  };

  const subscribers = [];

  function subscribe(fn) {
    subscribers.push(fn);
  }

  function notify() {
    subscribers.forEach((fn) => fn(state));
  }

  function setCurrentUser(user) {
    state.currentUser = user;
    if (!user || user.role !== "admin") {
      setActingAs(null);
    } else {
      notify();
    }
  }

  function getCurrentUser() {
    return state.currentUser;
  }

  function isAdmin() {
    return state.currentUser?.role === "admin";
  }

  function isManager() {
    return state.currentUser?.role === "manager";
  }

  function setActingAs(employeeId) {
    state.actingAsId = employeeId || null;
    if (employeeId) {
      localStorage.setItem(ACTING_AS_KEY, employeeId);
    } else {
      localStorage.removeItem(ACTING_AS_KEY);
    }
    notify();
  }

  function getActingAsId() {
    return state.actingAsId ? Number(state.actingAsId) : null;
  }

  function effectiveEmployeeId() {
    if (isAdmin() && getActingAsId()) return getActingAsId();
    return state.currentUser?.employee?.id ?? null;
  }

  function setEmployees(list) {
    state.employees = list;
    notify();
  }

  function getEmployees() {
    return state.employees;
  }

  function clear() {
    state.currentUser = null;
    state.employees = [];
    setActingAs(null);
  }

  return {
    subscribe,
    setCurrentUser,
    getCurrentUser,
    isAdmin,
    isManager,
    setActingAs,
    getActingAsId,
    effectiveEmployeeId,
    setEmployees,
    getEmployees,
    clear,
  };
})();
