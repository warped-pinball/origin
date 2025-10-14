const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

const code = fs.readFileSync(path.join(__dirname, 'auth.js'), 'utf8');

const store = {};
global.localStorage = {
  getItem: (k) => store[k],
  setItem: (k, v) => { store[k] = v; }
};
let replaced;
global.history = { replaceState: (a, b, url) => { replaced = url; } };
let cookieStore = 'token=abc';
global.document = {
  getElementById: () => null,
  get cookie() { return cookieStore; },
  set cookie(v) { cookieStore = v; }
};
global.displayPage = () => {};
global.loadUserInfo = () => {};
global.location = { search: '', pathname: '/', hash: '', protocol: 'https:' };
vm.runInThisContext(code);
let loggedIn = false;
let loginShown = false;
global.showLoggedIn = () => { loggedIn = true; };
global.showLogin = () => { loginShown = true; };

test('checkAuth keeps cookie and localStorage in sync', () => {
  store.token = undefined;
  loggedIn = false;
  loginShown = false;
  replaced = undefined;
  cookieStore = 'token=abc';
  checkAuth();
  assert.strictEqual(store.token, 'abc');
  assert.strictEqual(cookieStore, 'token=abc; path=/; SameSite=Lax; Secure');

  store.token = 'persisted';
  loggedIn = false;
  loginShown = false;
  replaced = undefined;
  cookieStore = '';
  checkAuth();
  assert.strictEqual(cookieStore, 'token=persisted; path=/; SameSite=Lax; Secure');
});
