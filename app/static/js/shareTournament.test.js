const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

const code = fs.readFileSync(path.join(__dirname, 'app.js'), 'utf8');

global.window = { location: { origin: 'https://example.com' }, API_BASE: '', addEventListener: () => {} };
global.document = { documentElement: { dataset: {} }, getElementById: () => null, querySelectorAll: () => [], addEventListener: () => {} };
global.navigator = {};
vm.runInThisContext(code);
global.showToast = () => {};
global.alert = () => {};

test('shareTournament', async (t) => {
  await t.test('uses single link when navigator.share available', () => {
    const tData = { id: 1, name: 'Test', start_time: new Date().toISOString() };
    const link = `${window.location.origin}/?tournament=${tData.id}`;
    let shared;
    navigator.share = (opts) => { shared = opts; };
    delete navigator.clipboard;
    shareTournament(tData);
    assert.strictEqual(shared.url, link);
    assert(!shared.text.includes(link));
  });

  await t.test('copies single link when navigator.share unavailable', () => {
    const tData = { id: 2, name: 'Test2', start_time: new Date().toISOString() };
    const link = `${window.location.origin}/?tournament=${tData.id}`;
    let copied;
    delete navigator.share;
    navigator.clipboard = { writeText: (msg) => { copied = msg; } };
    shareTournament(tData);
    const occurrences = copied.split(link).length - 1;
    assert.strictEqual(occurrences, 1);
  });
});

