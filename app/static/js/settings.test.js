const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

function createEl() {
  const el = {
    style: {},
    children: [],
    dataset: {},
    value: '',
    innerHTML: '',
    textContent: '',
    href: '',
    target: '',
    addEventListener() {},
    appendChild(child) { this.children.push(child); },
    removeAttribute(attr) { this[attr] = ''; },
    reset() {},
    scrollIntoView() { this.scrolled = true; }
  };
  let className = '';
  const classes = new Set();
  const syncClasses = () => {
    className = Array.from(classes).join(' ');
  };
  Object.defineProperty(el, 'className', {
    get() { return className; },
    set(value) {
      className = value || '';
      classes.clear();
      className.split(/\s+/).filter(Boolean).forEach(c => classes.add(c));
    }
  });
  el.classList = {
    add: (...cls) => { cls.forEach(c => classes.add(c)); syncClasses(); },
    remove: (...cls) => { cls.forEach(c => classes.delete(c)); syncClasses(); },
    contains: cls => classes.has(cls),
    toString: () => Array.from(classes).join(' ')
  };
  return el;
}

const elements = {};
function el(id) {
  if (!elements[id]) elements[id] = createEl();
  return elements[id];
}

global.document = {
  getElementById: id => el(id),
  createElement: tag => createEl(),
  querySelectorAll: () => ({ forEach: () => {} }),
  addEventListener: () => {}
};

global.showPage = () => {};
let lastToast = null;
global.showToast = (message, type) => { lastToast = { message, type }; };
global.history = { replaceState: () => {} };
global.location = { search: '', hash: '', pathname: '/', origin: 'https://origin.example', protocol: 'https:', host: 'origin.example' };
global.navigator = {
  clipboard: {
    writeText: async text => { global.__copiedText = text; }
  },
  share: async data => { global.__sharedData = data; }
};
global.open = (url, target) => { global.__openedWindow = { url, target }; };
global.confirm = () => true;

global.OriginApi = {
  getLocations: async () => ({ ok: true, json: async () => [] }),
  getMachines: async () => ({ ok: true, json: async () => [{ id: 1, name: 'M1', location_id: 1, qr_codes: [] }] }),
  assignMachine: async () => ({ ok: true }),
  removeMachine: async () => ({ ok: true }),
  createLocation: async () => ({ ok: true, json: async () => ({ id: 1 }) }),
  updateLocation: async () => ({ ok: true, json: async () => ({ id: 1 }) }),
  deleteLocation: async () => ({ ok: true }),
  getQrCodes: async () => ({ ok: true, json: async () => [] }),
  assignQrCode: async () => ({ ok: true, json: async () => ({}) })
};

const code = fs.readFileSync(path.join(__dirname, 'settings.js'), 'utf8');
vm.runInThisContext(code);

test('loadLocations sets pointer cursor', async () => {
  OriginApi.getLocations = async () => ({ ok: true, json: async () => [{ id: 1, name: 'Arc', address: 'Addr' }] });
  const list = el('locations-list');
  await loadLocations();
  assert.strictEqual(list.children.length, 1);
  assert.strictEqual(list.children[0].style.cursor, 'pointer');
});

test('openLocation shows view and edit button for owner', () => {
  __setCachedLocations([{ id: 1 }]);
  openLocation({ id: 1, name: 'Arcade', address: 'Addr', website: 'http://a', hours: '9-5' });
  assert.strictEqual(el('location-detail-form').style.display, 'none');
  assert.strictEqual(el('location-view').style.display, 'block');
  assert.strictEqual(el('edit-location-btn').style.display, 'block');
  assert.strictEqual(el('view-address').textContent, 'Addr');
});

test('enableLocationEdit toggles to form', () => {
  enableLocationEdit();
  assert.strictEqual(el('location-detail-form').style.display, 'block');
  assert.strictEqual(el('location-view').style.display, 'none');
  assert.strictEqual(el('detail-name').value, 'Arcade');
  assert.strictEqual(el('delete-location-btn').style.display, 'inline-flex');
});

test('openLocation hides edit for non-owner', () => {
  openLocation({ id: 2, name: 'Other' });
  assert.strictEqual(el('edit-location-btn').style.display, 'none');
});

test('openLocation rejects javascript protocol in website', () => {
  openLocation({ id: 3, name: 'Bad', website: 'javascript:alert(1)' });
  assert.strictEqual(el('view-website').href, '');
  assert.strictEqual(el('view-website').textContent, '');
});

test('openLocation configures dashboard actions', async () => {
  __setCachedLocations([{ id: 5 }]);
  global.__copiedText = '';
  global.__sharedData = null;
  global.__openedWindow = null;
  lastToast = null;
  openLocation({ id: 5, name: 'Test Place', address: '123 St', website: 'http://example.com' });
  const container = el('location-dashboard');
  assert.strictEqual(container.style.display, 'block');
  const link = el('location-dashboard-link');
  assert.strictEqual(link.href, 'https://origin.example/locations/5/display');
  await el('location-dashboard-copy').onclick({ preventDefault() {} });
  assert.strictEqual(global.__copiedText, 'https://origin.example/locations/5/display');
  assert.deepStrictEqual(lastToast, { message: 'Location link copied', type: 'success' });
  await el('location-dashboard-open').onclick({ preventDefault() {} });
  assert.deepStrictEqual(global.__openedWindow, { url: 'https://origin.example/locations/5/display', target: '_blank' });
  await el('location-dashboard-share').onclick({ preventDefault() {} });
  assert.strictEqual(global.__sharedData.url, 'https://origin.example/locations/5/display');
});

test('share button hidden when Web Share API unavailable', () => {
  const originalShare = global.navigator.share;
  delete global.navigator.share;
  openLocation({ id: 6, name: 'No Share' });
  assert.strictEqual(el('location-dashboard-share').style.display, 'none');
  global.navigator.share = originalShare;
});

test('loadMachines falls back to game title when name missing', async () => {
  OriginApi.getMachines = async () => ({ ok: true, json: async () => [{ id: 2, game_title: 'Pinball', location_id: null }] });
  const list = el('machines-list');
  list.children = [];
  list.innerHTML = '';
  await loadMachines();
  assert.ok(list.children.length > 0);
  assert.strictEqual(list.children[0].children[0].textContent, 'Pinball');
});

test('loadMachines highlights claimed machine and shows remove button', async () => {
  __setClaimedMachine('abc');
  OriginApi.getMachines = async () => ({ ok: true, json: async () => [{ id: 'abc', name: 'New Machine', location_id: null, qr_codes: [] }] });
  const list = el('machines-list');
  list.children = [];
  list.innerHTML = '';
  const message = el('machine-setup-message');
  await loadMachines();
  assert.strictEqual(list.children.length, 1);
  const li = list.children[0];
  assert.ok(li.classList.contains('machine-item'));
  assert.ok(li.classList.contains('machine-highlight'));
  assert.strictEqual(message.style.display, 'block');
  assert.strictEqual(li.children[1].children[1].textContent, 'Unregister');
});

test('loadMachines renders QR code details and allows copying', async () => {
  OriginApi.getMachines = async () => ({
    ok: true,
    json: async () => ([{
      id: 'qr-1',
      name: 'QR Machine',
      location_id: null,
      qr_codes: [{ id: 12, url: 'https://origin.example/q?r=abc123', code: 'abc123' }]
    }])
  });
  const list = el('machines-list');
  list.children = [];
  list.innerHTML = '';
  global.__copiedText = '';
  await loadMachines();
  assert.strictEqual(list.children.length, 1);
  const machineItem = list.children[0];
  const qrSection = machineItem.children.find(child => child.className && child.className.includes('machine-qr-section'));
  assert.ok(qrSection);
  const qrList = qrSection.children.find(child => child.className && child.className.includes('machine-qr-list'));
  assert.ok(qrList);
  const entry = qrList.children[0];
  const info = entry.children[0];
  assert.strictEqual(info.children[0].textContent, 'https://origin.example/q?r=abc123');
  const actions = entry.children[1];
  await actions.children[0].onclick({ preventDefault() {} });
  assert.strictEqual(global.__copiedText, 'https://origin.example/q?r=abc123');
});

test('loadQrCodes renders list and updates assignments', async () => {
  OriginApi.getMachines = async () => ({
    ok: true,
    json: async () => ([
      { id: 'm1', game_title: 'Machine One', location_id: null, qr_codes: [] },
      { id: 'm2', game_title: 'Machine Two', location_id: null, qr_codes: [] }
    ])
  });
  OriginApi.getQrCodes = async () => ({
    ok: true,
    json: async () => ([{
      id: 42,
      url: 'https://origin.example/q?r=xyz',
      code: 'xyz',
      machine_id: null,
      machine_label: null
    }])
  });
  let assignedId = null;
  let assignedMachine = null;
  OriginApi.assignQrCode = async (id, machineId) => {
    assignedId = id;
    assignedMachine = machineId;
    return {
      ok: true,
      json: async () => ({
        id,
        url: 'https://origin.example/q?r=xyz',
        code: 'xyz',
        machine_id: machineId,
        machine_label: machineId ? 'Machine One' : null
      })
    };
  };

  const list = el('qr-codes-list');
  list.children = [];
  list.innerHTML = '';
  el('qr-codes-empty').style.display = 'none';

  await loadMachines();
  await loadQrCodes();

  assert.strictEqual(list.children.length, 1);
  const item = list.children[0];
  const assignment = item.children[item.children.length - 1];
  const select = assignment.children[0];
  const status = assignment.children[1];
  assert.strictEqual(status.textContent, 'Not assigned');

  select.value = 'm1';
  await select.onchange();

  assert.strictEqual(assignedId, 42);
  assert.strictEqual(assignedMachine, 'm1');
  assert.deepStrictEqual(lastToast, { message: 'QR code updated', type: 'success' });

  const updatedItem = el('qr-codes-list').children[0];
  const updatedAssignment = updatedItem.children[updatedItem.children.length - 1];
  const updatedStatus = updatedAssignment.children[1];
  assert.strictEqual(updatedStatus.textContent, 'Assigned to Machine One');
});

test('handleLocationDelete removes location after confirmation', async () => {
  __setCachedLocations([{ id: 9, name: 'Delete Me' }]);
  OriginApi.getLocations = async () => ({ ok: true, json: async () => [] });
  OriginApi.getMachines = async () => ({ ok: true, json: async () => [] });
  openLocation({ id: 9, name: 'Delete Me' });
  enableLocationEdit();
  let confirmationMessage = '';
  global.confirm = message => { confirmationMessage = message; return true; };
  let deletedId = null;
  OriginApi.deleteLocation = async id => { deletedId = id; return { ok: true }; };
  await handleLocationDelete();
  assert.strictEqual(deletedId, 9);
  assert.ok(confirmationMessage.includes('Delete Me'));
  assert.strictEqual(el('location-detail-form').style.display, 'none');
  assert.strictEqual(el('location-view').style.display, 'none');
  assert.strictEqual(el('delete-location-btn').style.display, 'none');
  global.confirm = () => true;
});

test('handleLocationDelete aborts when user cancels', async () => {
  __setCachedLocations([{ id: 11, name: 'Keep Me' }]);
  openLocation({ id: 11, name: 'Keep Me' });
  enableLocationEdit();
  let called = false;
  OriginApi.deleteLocation = async () => { called = true; return { ok: true }; };
  global.confirm = () => false;
  await handleLocationDelete();
  assert.strictEqual(called, false);
  global.confirm = () => true;
});
