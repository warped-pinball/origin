const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const buildSW = require('../scripts/build-sw');

function makeStaticDir() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'swtest-'));
  fs.writeFileSync(path.join(dir, 'offline.html'), '<html></html>');
  fs.writeFileSync(path.join(dir, 'app.js'), '');
  fs.writeFileSync(path.join(dir, 'api.js'), '');
  fs.writeFileSync(path.join(dir, 'manifest.json'), '{}');
  fs.writeFileSync(path.join(dir, 'logo.png'), '');
  return dir;
}

test('build-sw injects offline fallback', async () => {
  const dir = makeStaticDir();
  await buildSW(dir);
  const sw = fs.readFileSync(path.join(dir, 'service-worker.js'), 'utf8');
  assert(sw.includes('offline.html'));
});
