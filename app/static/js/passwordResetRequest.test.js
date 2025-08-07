const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

const code = fs.readFileSync(path.join(__dirname, 'api.js'), 'utf8');

global.API_BASE = '';
let called;
global.fetch = async (url, opts) => { called = { url, opts }; return { ok: true }; };
vm.runInThisContext(code);

const { requestPasswordReset } = OriginApi;

test('requestPasswordReset sends correct request', async () => {
  await requestPasswordReset('user@example.com');
  assert.strictEqual(called.url, '/api/v1/auth/password-reset/request');
  assert.strictEqual(called.opts.method, 'POST');
  assert.strictEqual(called.opts.headers['Content-Type'], 'application/json');
  assert.strictEqual(called.opts.body, JSON.stringify({ email: 'user@example.com' }));
});
