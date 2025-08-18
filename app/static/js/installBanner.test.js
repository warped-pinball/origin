const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');

test('install banner contains a single close button', () => {
  const html = fs.readFileSync(path.join(__dirname, '..', '..', 'templates', 'index.html'), 'utf8');
  const matches = html.match(/class=['"][^'"]*banner-close[^'"]*['"]/g) || [];
  assert.strictEqual(matches.length, 1);
});
