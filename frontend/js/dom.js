const Dom = (() => {
  function escapeHtml(value) {
    if (value === null || value === undefined) return "";
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function qs(selector, root = document) {
    return root.querySelector(selector);
  }

  function loading(container, message = "Loading…") {
    container.innerHTML = `<div class="loading-state">${escapeHtml(message)}</div>`;
  }

  function empty(container, message) {
    container.innerHTML = `<div class="empty-state">${escapeHtml(message)}</div>`;
  }

  function errorState(container, message) {
    container.innerHTML = `<div class="alert alert-error">${escapeHtml(message)}</div>`;
  }

  function errorMessage(err) {
    if (err && err.body) {
      if (err.body.errors) {
        return Object.entries(err.body.errors)
          .map(([field, msgs]) => `${field}: ${[].concat(msgs).join(", ")}`)
          .join(" | ");
      }
      if (err.body.message) return err.body.message;
    }
    return (err && err.message) || "Something went wrong";
  }

  return { escapeHtml, qs, loading, empty, errorState, errorMessage };
})();
