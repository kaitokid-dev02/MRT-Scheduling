// Tiny fetch wrapper shared by the dashboard. Adds the CSRF header and
// turns every failure (HTTP or network) into a thrown Error with a message.
(function () {
  const csrf = () => document.querySelector('meta[name="csrf-token"]')?.content || '';

  async function request(url, options = {}) {
    let response;
    try {
      response = await fetch(url, {
        ...options,
        headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf(), ...(options.headers || {}) },
      });
    } catch {
      throw new Error('Network error — check the connection and try again.');
    }
    let data = {};
    try { data = await response.json(); } catch { /* non-JSON error body */ }
    if (!response.ok || data.ok === false) {
      throw new Error(data.error || `Request failed (${response.status}).`);
    }
    return data;
  }

  window.Api = {
    get: (url) => request(url),
    post: (url, body = {}) => request(url, { method: 'POST', body: JSON.stringify(body) }),
  };
})();
