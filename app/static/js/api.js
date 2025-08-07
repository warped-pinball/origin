(function (global) {
  function createOriginApi(base = global.API_BASE || '') {
    const API_BASE = base;

    async function signup(email, password, screenName) {
      return fetch(API_BASE + '/api/v1/users/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, screen_name: screenName })
      });
    }

    async function login(email, password) {
      return fetch(API_BASE + '/api/v1/auth/token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({ username: email, password })
      });
    }

    async function getMe() {
      return apiFetch('/api/v1/users/me');
    }

    async function updateScreenName(screenName) {
      return apiFetch('/api/v1/users/me', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ screen_name: screenName })
      });
    }

    async function updatePassword(password) {
      return apiFetch('/api/v1/users/me/password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password })
      });
    }

    async function deleteAccount() {
      return apiFetch('/api/v1/users/me', {
        method: 'DELETE'
      });
    }

    return {
      signup,
      login,
      getMe,
      updateScreenName,
      updatePassword,
      deleteAccount
    };
  }

  global.createOriginApi = createOriginApi;
  global.OriginApi = createOriginApi();
})(typeof window !== 'undefined' ? window : this);
