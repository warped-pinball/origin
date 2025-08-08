const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

const code = fs.readFileSync(path.join(__dirname, 'pwa.js'), 'utf8');

let beforeHandler;
let installHandler;
const dialog = {
  showModalCalled: false,
  closeCalled: false,
  showModal() { this.showModalCalled = true; },
  close() { this.closeCalled = true; }
};

global.window = {
  addEventListener: (event, handler) => {
    if (event === 'beforeinstallprompt') beforeHandler = handler;
    if (event === 'appinstalled') installHandler = handler;
  }
};

global.document = {
  getElementById: () => dialog
};

vm.runInThisContext(code);

test('shows dialog and installs app', async () => {
  const ev = {
    preventDefault() {},
    prompt: () => { ev.promptCalled = true; return Promise.resolve(); },
    userChoice: Promise.resolve({ outcome: 'accepted' })
  };
  beforeHandler(ev);
  assert.ok(dialog.showModalCalled);
  await installApp();
  assert.ok(ev.promptCalled);
  assert.ok(dialog.closeCalled);
  assert.strictEqual(deferredPrompt, null);
});

test('appinstalled handler clears prompt and closes dialog', () => {
  dialog.closeCalled = false;
  deferredPrompt = {};
  installHandler();
  assert.ok(dialog.closeCalled);
  assert.strictEqual(deferredPrompt, null);
});
