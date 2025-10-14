const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

const code = fs.readFileSync(path.join(__dirname, 'pwa.js'), 'utf8');

let beforeHandler;
let installHandler;
let installClick;
let closeClick;
const banner = { hidden: true };
const installBtn = {
  addEventListener: (event, handler) => {
    if (event === 'click') installClick = handler;
  }
};
const closeBtn = {
  addEventListener: (event, handler) => {
    if (event === 'click') closeClick = handler;
  }
};

global.window = {
  addEventListener: (event, handler) => {
    if (event === 'beforeinstallprompt') beforeHandler = handler;
    if (event === 'appinstalled') installHandler = handler;
  }
};

global.document = {
  getElementById: (id) => {
    if (id === 'install-banner') return banner;
    if (id === 'install-button') return installBtn;
    if (id === 'install-close-button') return closeBtn;
    return null;
  }
};

vm.runInThisContext(code);

test('shows banner and installs app', async () => {
  const ev = {
    preventDefault() {},
    prompt: () => { ev.promptCalled = true; return Promise.resolve(); },
    userChoice: Promise.resolve({ outcome: 'accepted' })
  };
  beforeHandler(ev);
  assert.strictEqual(banner.hidden, false);
  assert.strictEqual(typeof installClick, 'function');
  await window.installApp();
  assert.ok(ev.promptCalled);
  assert.strictEqual(banner.hidden, true);
  assert.strictEqual(deferredPrompt, null);
});

test('appinstalled handler clears prompt and hides banner', () => {
  banner.hidden = false;
  deferredPrompt = {};
  installHandler();
  assert.strictEqual(banner.hidden, true);
  assert.strictEqual(deferredPrompt, null);
});

test('assigns functions to window', () => {
  assert.strictEqual(typeof window.installApp, 'function');
  assert.strictEqual(typeof window.closeInstall, 'function');
});

test('closeInstall hides banner', () => {
  banner.hidden = false;
  window.closeInstall();
  assert.strictEqual(banner.hidden, true);
  assert.strictEqual(typeof closeClick, 'function');
});

test('click handlers invoke install and close logic', async () => {
  banner.hidden = false;
  const ev = {
    preventDefault() {},
    prompt: () => { ev.promptCalled = true; return Promise.resolve(); },
    userChoice: Promise.resolve({ outcome: 'dismissed' })
  };
  beforeHandler(ev);
  await installClick();
  assert.ok(ev.promptCalled);
  assert.strictEqual(banner.hidden, true);
  banner.hidden = false;
  closeClick();
  assert.strictEqual(banner.hidden, true);
});
