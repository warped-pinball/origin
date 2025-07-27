const fs = require('fs');
const path = require('path');

const src = path.join(__dirname, '../www/logo.png');
const dest = path.join(
  __dirname,
  '../platforms/android/app/src/main/res/drawable/logo.png'
);

try {
  if (fs.existsSync(src)) {
    fs.mkdirSync(path.dirname(dest), { recursive: true });
    fs.copyFileSync(src, dest);
    console.log(`Copied ${src} to ${dest}`);
  }
} catch (err) {
  console.error('Failed to copy logo:', err.message);
}
