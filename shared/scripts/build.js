const fs = require('fs');
const path = require('path');

const src = path.resolve(__dirname, '../../sdks/typescript');
const distFile = path.join(src, 'index.js');
const dist = path.resolve(__dirname, '../dist/api.js');
fs.mkdirSync(path.dirname(dist), { recursive: true });
fs.copyFileSync(distFile, dist);

const serverDest = path.resolve(__dirname, '../../app/static/api.js');
const mobileDest = path.resolve(__dirname, '../../mobile/www/api.js');

fs.copyFileSync(dist, serverDest);
fs.copyFileSync(dist, mobileDest);

console.log('API client built to', serverDest, 'and', mobileDest);
