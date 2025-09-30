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
global.showToast = () => {};
global.history = { replaceState: () => {} };
global.location = { search: '', hash: '', pathname: '/' };

global.OriginApi = {
  getLocations: async () => ({ ok: true, json: async () => [] }),
  getMachines: async () => ({ ok: true, json: async () => [{ id: 1, name: 'M1', location_id: 1 }] }),
  assignMachine: async () => ({ ok: true }),
  removeMachine: async () => ({ ok: true }),
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
  OriginApi.getMachines = async () => ({ ok: true, json: async () => [{ id: 'abc', name: 'New Machine', location_id: null }] });
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
