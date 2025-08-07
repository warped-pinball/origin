(function (global) {
  const BASE = global.API_BASE || '';

  async function apiFetch(path, options = {}) {
    const opts = { ...options };
    opts.headers = opts.headers || {};
    const token = global.localStorage?.getItem('token');
    if (token) {
      opts.headers['Authorization'] = 'Bearer ' + token;
    }
    const res = await fetch(BASE + path, opts);
    if (res.status === 401) {
      try {
        global.localStorage?.removeItem('token');
      } catch {}
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
