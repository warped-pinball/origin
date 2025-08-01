(function (global) {
  async function createOriginApi(base = global.API_BASE || '', opts = {}) {
    let OpenAPIClientAxios = opts.OpenAPIClientAxios;
    if (!OpenAPIClientAxios) {
      if (typeof require === 'function') {
        try { OpenAPIClientAxios = require('openapi-client-axios').default; } catch {}
      }
      if (!OpenAPIClientAxios && global.OpenAPIClientAxios) {
        OpenAPIClientAxios = global.OpenAPIClientAxios;
      }
      if (!OpenAPIClientAxios) {
        const mod = await import('https://cdn.jsdelivr.net/npm/openapi-client-axios/browser/index.js');
        OpenAPIClientAxios = mod.default;
      }
    }

    const definition = opts.definition || `${base}/openapi.json`;
    const axiosConfigDefaults = Object.assign({ baseURL: base }, opts.axiosConfig || {});
    const api = new OpenAPIClientAxios({ definition, axiosConfigDefaults });
    const client = await api.init();

    return {
      signup(email, password, screenName) {
        return client.create_user_api_v1_users__post(null, { email, password, screen_name: screenName });
      },
      login(email, password) {
        const data = new URLSearchParams({ username: email, password });
        return client.login_for_access_token_api_v1_auth_token_post(null, data, {
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
        });
      },
      getMe(token) {
        return client.read_users_me_api_v1_users_me_get(null, null, {
          headers: { Authorization: 'Bearer ' + token }
        });
      },
      updateScreenName(token, screenName) {
        return client.update_me_api_v1_users_me_patch(null, { screen_name: screenName }, {
          headers: { Authorization: 'Bearer ' + token }
        });
      },
      updatePassword(token, password) {
        return client.change_password_api_v1_users_me_password_post(null, { password }, {
          headers: { Authorization: 'Bearer ' + token }
        });
      },
      deleteAccount(token) {
        return client.delete_me_api_v1_users_me_delete(null, null, {
          headers: { Authorization: 'Bearer ' + token }
        });
      }
    };
  }

  if (typeof module === 'object' && module.exports) {
    module.exports = createOriginApi;
  } else {
    global.createOriginApi = createOriginApi;
  }
})(typeof window !== 'undefined' ? window : globalThis);
