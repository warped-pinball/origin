(function (global) {
  const BASE = global.API_BASE || '';

  async function apiFetch(path, options = {}) {
    const opts = { ...options };
    opts.headers = opts.headers || {};
    opts.credentials = 'include';
    const res = await fetch(BASE + path, opts);
    if (res.status === 401) {
      if (typeof global.showLogin === 'function') {
        global.showLogin();
      } else if (global.location) {
        global.location.href = 'login.html';
      }
      throw new Error('Unauthorized');
    }
    return res;
  }

  global.apiFetch = apiFetch;
})(typeof window !== 'undefined' ? window : globalThis);
