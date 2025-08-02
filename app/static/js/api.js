(function (global) {
  function createOriginApi(base = global.API_BASE || '') {
    const API_BASE = base;

    async function signup(phone, password, screenName) {
      return fetch(API_BASE + '/api/v1/users/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone, password, screen_name: screenName })
      });
    }

    async function login(phone, password) {
      return fetch(API_BASE + '/api/v1/auth/token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({ username: phone, password })
      });
    }

    async function getMe(token) {
      return fetch(API_BASE + '/api/v1/users/me', {
        headers: { 'Authorization': 'Bearer ' + token }
      });
    }

    async function updateScreenName(token, screenName) {
      return fetch(API_BASE + '/api/v1/users/me', {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer ' + token
        },
        body: JSON.stringify({ screen_name: screenName })
      });
    }

    async function updatePassword(token, password) {
      return fetch(API_BASE + '/api/v1/users/me/password', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer ' + token
        },
        body: JSON.stringify({ password })
      });
    }

    async function deleteAccount(token) {
      return fetch(API_BASE + '/api/v1/users/me', {
        method: 'DELETE',
        headers: { 'Authorization': 'Bearer ' + token }
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
