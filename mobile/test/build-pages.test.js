const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');
const { execFileSync } = require('node:child_process');

test('build-pages generates pages with partials', () => {
  // run the build script
  execFileSync('node', [path.join('scripts', 'build-pages.js')]);

  const head = fs.readFileSync(path.join('www', 'partials', 'head.html'), 'utf8');
  const nav = fs.readFileSync(path.join('www', 'partials', 'nav.html'), 'utf8');

  const templateDir = path.join('www', 'templates');
  for (const file of fs.readdirSync(templateDir)) {
    if (!file.endsWith('.html')) continue;
    const template = fs.readFileSync(path.join(templateDir, file), 'utf8');
    const pkg = require('../package.json');
    const expected = template
      .replace('{{head}}', head)
      .replace('{{nav}}', nav)
      .replace(/{{version}}/g, pkg.version)
      .replace(/{{apiBase}}/g, process.env.PUBLIC_API_URL || require('../api-base'));
    const output = fs.readFileSync(path.join('www', file), 'utf8');
    assert.strictEqual(output, expected);
  }
});
