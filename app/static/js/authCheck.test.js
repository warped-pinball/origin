const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

const code = fs.readFileSync(path.join(__dirname, 'auth.js'), 'utf8');

const store = {};
let setCalled = false;
global.localStorage = {
  getItem: (k) => store[k],
  setItem: (k, v) => { setCalled = true; store[k] = v; }
};
global.OriginApi = {
  getMe: async () => ({ ok: false })
};

global.history = { replaceState: () => {} };
global.document = { getElementById: () => null };
global.displayPage = () => {};
global.loadUserInfo = () => {};
global.location = { search: '?token=abc', pathname: '/', hash: '' };

vm.runInThisContext(code);



test('checkAuth does not store token', async () => {
  setCalled = false;
  await checkAuth();
  assert.strictEqual(setCalled, false);
  assert.strictEqual(store.token, undefined);
});
