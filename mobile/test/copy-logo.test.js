const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');
const { execFileSync } = require('node:child_process');

test(
  'copy-logo copies logo to android resources',
  { concurrency: false },
  () => {
    const srcFile = path.join('www', 'logo.svg');
    fs.writeFileSync(srcFile, '');
    const destDir = path.join(
      'platforms',
      'android',
      'app',
      'src',
      'main',
      'res',
      'drawable'
    );
    fs.rmSync(destDir, { recursive: true, force: true });
    const destFile = path.join(destDir, 'logo.svg');
    execFileSync('node', [path.join('scripts', 'copy-logo.js')]);
    assert(fs.existsSync(destFile));
    fs.rmSync(srcFile, { force: true });
  }
);
