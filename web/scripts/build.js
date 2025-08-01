const fs = require('fs');
const path = require('path');

const src = path.resolve(__dirname, '../../sdks/typescript/dist');
const distFile = path.join(src, 'index.js');
const dist = path.resolve(__dirname, '../dist/api.js');
fs.mkdirSync(path.dirname(dist), { recursive: true });
fs.copyFileSync(distFile, dist);

const serverDest = path.resolve(__dirname, '../../app/static/js/api.js');
fs.copyFileSync(dist, serverDest);

console.log('API client built to', serverDest);
