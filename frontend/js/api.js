const Api = (() => {
  const BASE_URL = "/api";

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
      throw new Error(message);
    }
    return body;
  }

  return {
    health: () => request("/health"),
    get: (path) => request(path),
    post: (path, data) => request(path, { method: "POST", body: JSON.stringify(data) }),
    put: (path, data) => request(path, { method: "PUT", body: JSON.stringify(data) }),
    del: (path) => request(path, { method: "DELETE" }),
  };
})();