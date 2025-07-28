const test = require('node:test');
const assert = require('node:assert');
const path = require('node:path');
const fs = require('node:fs');
const vm = require('node:vm');

const SRC = path.join(__dirname, '../src/api.js');

function loadApi(fetchImpl, apiBase) {
  const code = fs.readFileSync(SRC, 'utf8');
  const sandbox = { fetch: fetchImpl };
  Object.setPrototypeOf(sandbox, global);
  vm.runInNewContext(code, sandbox, { filename: SRC });
  return sandbox.createOriginApi(apiBase);
}

test('signup posts to /users/', async () => {
  const calls = [];
  const api = loadApi((url, opts) => { calls.push({ url, opts }); return Promise.resolve({}); }, 'http://x');
  await api.signup('a@b.c', 'p', 'n');
  assert.strictEqual(calls.length, 1);
  assert.strictEqual(calls[0].url, 'http://x/api/v1/users/');
  assert.strictEqual(calls[0].opts.method, 'POST');
});

test('login posts form data', async () => {
  const calls = [];
  const api = loadApi((url, opts) => { calls.push({ url, opts }); return Promise.resolve({}); }, 'http://x');
  await api.login('a@b.c', 'p');
  assert.strictEqual(calls[0].url, 'http://x/api/v1/auth/token');
  assert.strictEqual(calls[0].opts.method, 'POST');
  assert(/username=a%40b.c/.test(calls[0].opts.body.toString()));
});

test('updateScreenName uses token', async () => {
  const calls = [];
  const api = loadApi((url, opts) => { calls.push({ url, opts }); return Promise.resolve({}); }, '');
  await api.updateScreenName('t', 'name');
  assert.strictEqual(calls[0].opts.headers.Authorization, 'Bearer t');
});

test('updatePassword uses token', async () => {
  const calls = [];
  const api = loadApi((url, opts) => { calls.push({ url, opts }); return Promise.resolve({}); }, '');
  await api.updatePassword('tok', 'p');
  assert.strictEqual(calls[0].opts.headers.Authorization, 'Bearer tok');
});

test('deleteAccount sends DELETE', async () => {
  const calls = [];
  const api = loadApi((url, opts) => { calls.push({ url, opts }); return Promise.resolve({}); }, 'base');
  await api.deleteAccount('t');
  assert.strictEqual(calls[0].opts.method, 'DELETE');
  assert.strictEqual(calls[0].url, 'base/api/v1/users/me');
});
