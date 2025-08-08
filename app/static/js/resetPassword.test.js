const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

let toast;
global.showToast = (msg, type) => { toast = { msg, type }; };

global.OriginApi = {
  resetPassword: async () => ({ ok: true })
};

const elements = {
  'new-password': { value: 'newpass' },
  'confirm-submit': { disabled: false },
  'confirm-spinner': { style: { display: 'none' } },
  'confirm-error': { style: { color: '' }, textContent: '' }
};

global.document = {
  getElementById: id => elements[id] || null,
  addEventListener: () => {}
};

global.location = { search: '', href: '/reset-password' };

global.setTimeout = fn => fn();

const code = fs.readFileSync(path.join(__dirname, 'reset_password.js'), 'utf8');
vm.runInThisContext(code);

test('successful reset shows message and redirects', async () => {
  global.location.search = '?token=tok';
  await resetPassword({ preventDefault() {} });
  assert.strictEqual(toast.msg, 'Password reset. You can now log in.');
  assert.strictEqual(toast.type, 'success');
  assert.strictEqual(global.location.href, '/');
});
