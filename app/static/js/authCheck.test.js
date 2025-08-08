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
let redirected;
global.history = { replaceState: (a, b, url) => { replaced = url; } };
global.document = { getElementById: () => null };
global.displayPage = () => {};
global.loadUserInfo = () => {};
global.location = { search: '?token=abc', pathname: '/', hash: '' };
vm.runInThisContext(code);
test('checkAuth stores token from query', () => {
  replaced = undefined;
  global.location = { search: '?token=abc', pathname: '/', hash: '' };
  checkAuth();
  assert.strictEqual(store.token, 'abc');
  assert.strictEqual(replaced, '/');
});

test('checkAuth rejects external next URLs', () => {
  replaced = undefined;
  redirected = undefined;
  store.token = 'abc';
  global.location = {
    search: '?next=https://evil.com',
    pathname: '/',
    hash: '',
    origin: 'http://example.com',
    set href(v) { redirected = v; }
  };
  checkAuth();
  assert.strictEqual(redirected, undefined);
  assert.strictEqual(replaced, '/');
});
