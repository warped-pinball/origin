const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');

const swPath = path.resolve(__dirname, '../../app/static/service-worker.js');

test('service worker is minimal and workbox-free', () => {
  const sw = fs.readFileSync(swPath, 'utf8');
  assert(sw.includes('skipWaiting'));
  assert(sw.includes('clients.claim'));
  assert(!sw.includes('workbox'));
});
