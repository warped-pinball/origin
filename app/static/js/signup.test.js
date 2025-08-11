const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

const code = fs.readFileSync(path.join(__dirname, 'signup.js'), 'utf8');

let showToastCalled = false;
global.showToast = () => { showToastCalled = true; };
global.logToFile = () => {};

const errEl = { textContent: '', innerHTML: '' };
const spinner = { style: {} };
const btn = { disabled: false };
const elements = {
  'signup-email': { value: 'user@example.com' },
  'signup-password': { value: 'pass' },
  'signup-screen': { value: 'User' },
  'signup-submit': btn,
  'signup-spinner': spinner,
  'signup-error': errEl,
};

global.document = {
  getElementById: (id) => elements[id],
  addEventListener: () => {}
};

global.OriginApi = {
  signup: async () => ({ ok: false, status: 400, json: async () => ({ detail: 'Email already registered' }) })
};

vm.runInThisContext(code);

test('signup shows duplicate email message', async () => {
  await signup({ preventDefault() {} });
  assert.ok(errEl.innerHTML.includes('Email already registered'));
  assert.ok(errEl.innerHTML.includes('reset-password'));
  assert.strictEqual(showToastCalled, false);
});
