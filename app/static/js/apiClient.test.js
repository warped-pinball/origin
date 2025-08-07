const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

const code = fs.readFileSync(path.join(__dirname, 'http.js'), 'utf8');

global.API_BASE = '';
let redirected = false;
global.showLogin = () => { redirected = true; };
const store = { token: 'abc' };
global.localStorage = {
  getItem: (k) => store[k],
  setItem: (k, v) => { store[k] = v; },
  removeItem: (k) => { delete store[k]; }
};
global.location = { href: 'index.html' };
global.fetch = async () => ({ status: 401 });
vm.runInThisContext(code);

test('apiFetch redirects on 401', async (t) => {
  redirected = false;
  await apiFetch('/secret').catch(() => {});
  assert.strictEqual(redirected, true);
  assert.strictEqual(localStorage.getItem('token'), undefined);
});
