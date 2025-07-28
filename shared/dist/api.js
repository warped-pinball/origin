(function (global) {
  const API_BASE = global.API_BASE || '';

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

  global.OriginApi = {
    signup,
    login,
    updateScreenName,
    updatePassword,
    deleteAccount
  };
})(typeof window !== 'undefined' ? window : this);
