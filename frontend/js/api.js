const Api = (() => {
  const BASE_URL = "/api";

  function buildQuery(params = {}) {
    const entries = Object.entries(params).filter(
      ([, v]) => v !== undefined && v !== null && v !== ""
    );
    if (entries.length === 0) return "";
    const search = new URLSearchParams();
    entries.forEach(([k, v]) => search.set(k, v));
    return `?${search.toString()}`;
  }

  async function request(path, options = {}) {
    const token = localStorage.getItem("access_token");
    const headers = {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    };

    const response = await fetch(`${BASE_URL}${path}`, { ...options, headers });
    const isJson = response.headers.get("content-type")?.includes("application/json");
    const body = isJson ? await response.json() : null;

    if (!response.ok) {
      const message = body?.message || `Request failed with status ${response.status}`;
      const error = new Error(message);
      error.status = response.status;
      error.body = body;
      throw error;
    }
    return body;
  }

  const get = (path) => request(path);
  const post = (path, data) => request(path, { method: "POST", body: JSON.stringify(data ?? {}) });
  const put = (path, data) => request(path, { method: "PUT", body: JSON.stringify(data ?? {}) });
  const del = (path) => request(path, { method: "DELETE" });

  return {
    health: () => get("/health"),
    get,
    post,
    put,
    del,

    teams: {
      list: () => get("/teams"),
      create: (name) => post("/teams", { name }),
    },

    employees: {
      list: (params) => get(`/employees${buildQuery(params)}`),
      get: (id) => get(`/employees/${id}`),
      create: (data) => post("/employees", data),
      update: (id, data) => put(`/employees/${id}`, data),
      deactivate: (id) => post(`/employees/${id}/deactivate`),
      reactivate: (id) => post(`/employees/${id}/reactivate`),
      orgChart: (includeInactive) =>
        get(`/employees/org-chart${buildQuery({ include_inactive: includeInactive })}`),
    },

    leave: {
      list: (params) => get(`/leave-requests${buildQuery(params)}`),
      get: (id) => get(`/leave-requests/${id}`),
      submit: (data) => post("/leave-requests", data),
      approve: (id, data) => post(`/leave-requests/${id}/approve`, data),
      reject: (id, data) => post(`/leave-requests/${id}/reject`, data),
      cancel: (id, data) => post(`/leave-requests/${id}/cancel`, data),
      pendingApprovals: (managerId) =>
        get(`/leave-requests/pending-approvals${buildQuery({ manager_id: managerId })}`),
      onLeave: (date) => get(`/leave-requests/on-leave${buildQuery({ date })}`),
      balances: (employeeId, year) =>
        get(`/leave-requests/balances${buildQuery({ employee_id: employeeId, year })}`),
      escalate: () => post("/leave-requests/escalate"),
    },

    payroll: {
      generate: (data) => post("/payroll/generate", data),
      finalize: (periodId) => post(`/payroll/periods/${periodId}/finalize`),
      periods: (params) => get(`/payroll/periods${buildQuery(params)}`),
      period: (id) => get(`/payroll/periods/${id}`),
      entries: (periodId, params) => get(`/payroll/periods/${periodId}/entries${buildQuery(params)}`),
      payslip: (periodId, employeeId) =>
        get(`/payroll/periods/${periodId}/entries/${employeeId}`),
      employeeEntries: (employeeId) => get(`/payroll/employees/${employeeId}/entries`),
    },
  };
})();
