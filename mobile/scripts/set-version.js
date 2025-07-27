const fs = require('fs');
const path = require('path');

const version = process.argv[2] || process.env.VERSION || require('../package.json').version;

function updateJSON(file, cb) {
  const json = JSON.parse(fs.readFileSync(file, 'utf8'));
  if (cb(json)) {
    fs.writeFileSync(file, JSON.stringify(json, null, 2) + '\n', 'utf8');
    console.log(`Updated ${path.basename(file)} to ${version}`);
  }
}

updateJSON(path.join(__dirname, '../package.json'), json => {
  if (json.version !== version) {
    json.version = version;
    return true;
  }
});

const lockFile = path.join(__dirname, '../package-lock.json');
if (fs.existsSync(lockFile)) {
  updateJSON(lockFile, json => {
    let changed = false;
    if (json.version !== version) {
      json.version = version;
      changed = true;
    }
    if (json.packages && json.packages[''] && json.packages[''].version !== version) {
      json.packages[''].version = version;
      changed = true;
    }
    return changed;
  });
}

const configPath = path.join(__dirname, '../config.xml');
let config = fs.readFileSync(configPath, 'utf8');
const updated = config.replace(/version="[^"]+"/, `version="${version}"`);
if (updated !== config) {
  fs.writeFileSync(configPath, updated, 'utf8');
  console.log(`Updated config.xml to ${version}`);
}
