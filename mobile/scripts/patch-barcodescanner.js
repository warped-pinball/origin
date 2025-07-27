const fs = require('fs');
const path = require('path');

function patch(file) {
  let content = fs.readFileSync(file, 'utf8');
  const updated = content
    .replace(/jcenter\(\)/g, 'google()\n    mavenCentral()')
    .replace(/compile\(/g, 'implementation(');
  if (content !== updated) {
    fs.writeFileSync(file, updated, 'utf8');
    console.log(`Patched ${file}`);
  }
}

const pluginGradle = path.join(
  __dirname,
  '../plugins/phonegap-plugin-barcodescanner/src/android/barcodescanner.gradle'
);
const platformDir = path.join(
  __dirname,
  '../platforms/android/phonegap-plugin-barcodescanner'
);

if (fs.existsSync(pluginGradle)) {
  patch(pluginGradle);
}

if (fs.existsSync(platformDir)) {
  fs.readdirSync(platformDir)
    .filter((f) => f.endsWith('.gradle'))
    .forEach((f) => patch(path.join(platformDir, f)));
}
