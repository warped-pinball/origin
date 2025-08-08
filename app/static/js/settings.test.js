const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

  function createEl() {
  return {
    style: {},
    children: [],
    appendChild(child) { this.children.push(child); },
    addEventListener() {},
    reset() {},
    dataset: {},
    value: '',
    innerHTML: '',
    textContent: '',
    href: '',
    target: '',
    removeAttribute(attr) { this[attr] = ''; }
  };
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
global.showToast = () => {};

global.OriginApi = {
  getLocations: async () => ({ ok: true, json: async () => [] }),
  getMachines: async () => ({ ok: true, json: async () => [{ id: 1, name: 'M1', location_id: 1 }] }),
  assignMachine: async () => ({ ok: true }),
  createLocation: async () => ({ ok: true, json: async () => ({ id: 1 }) }),
  updateLocation: async () => ({ ok: true, json: async () => ({ id: 1 }) })
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

