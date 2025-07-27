const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');
const { execFileSync } = require('node:child_process');

const pluginDir = path.join('plugins', 'phonegap-plugin-barcodescanner', 'src', 'android');
const platformDir = path.join('platforms', 'android', 'phonegap-plugin-barcodescanner');

function setup() {
  fs.mkdirSync(pluginDir, { recursive: true });
  fs.mkdirSync(platformDir, { recursive: true });
  fs.writeFileSync(path.join(pluginDir, 'barcodescanner.gradle'), 'repositories {\n    jcenter()\n}\ndependencies {\n    compile("x")\n}');
  fs.writeFileSync(path.join(platformDir, 'build.gradle'), 'repositories {\n    jcenter()\n}\ndependencies {\n    compile("x")\n}');
}

function cleanup() {
  fs.rmSync('plugins', { recursive: true, force: true });
  fs.rmSync('platforms', { recursive: true, force: true });
}

test('patch-barcodescanner patches gradle files', { concurrency: false }, () => {
  setup();
  try {
    execFileSync('node', [path.join('scripts', 'patch-barcodescanner.js')]);

    const pluginContent = fs.readFileSync(path.join(pluginDir, 'barcodescanner.gradle'), 'utf8');
    assert(pluginContent.includes('google()'));
    assert(pluginContent.includes('mavenCentral()'));
    assert(!pluginContent.includes('compile('));
    assert(pluginContent.includes('implementation('));

    const platformContent = fs.readFileSync(path.join(platformDir, 'build.gradle'), 'utf8');
    assert(platformContent.includes('google()'));
    assert(platformContent.includes('mavenCentral()'));
    assert(!platformContent.includes('compile('));
    assert(platformContent.includes('implementation('));
  } finally {
    cleanup();
  }
});
