const Store = (() => {
  const ACTING_AS_KEY = "hr_acting_as_employee_id";

  const state = {
    actingAsId: localStorage.getItem(ACTING_AS_KEY) || null,
    employees: [], // all employees (active + inactive), cached for dropdowns
  };

  const subscribers = [];

  function subscribe(fn) {
    subscribers.push(fn);
  }

  function notify() {
    subscribers.forEach((fn) => fn(state));
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

  function getActingAsEmployee() {
    const id = getActingAsId();
    return state.employees.find((e) => e.id === id) || null;
  }

  function setEmployees(list) {
    state.employees = list;
    // If the previously acting-as employee no longer exists (fresh DB reset,
    // etc.), fall back gracefully instead of leaving a dangling id selected.
    if (state.actingAsId && !getActingAsEmployee()) {
      setActingAs(list.length ? list[0].id : null);
    } else {
      notify();
    }
  }

  function getEmployees() {
    return state.employees;
  }

  return {
    subscribe,
    setActingAs,
    getActingAsId,
    getActingAsEmployee,
    setEmployees,
    getEmployees,
  };
})();
