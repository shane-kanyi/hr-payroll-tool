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
});