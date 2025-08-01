const fs = require('fs');
const path = require('path');

const dist = path.resolve(__dirname, '../dist/api.js');
const serverDest = path.resolve(__dirname, '../../app/static/js/api.js');
fs.mkdirSync(path.dirname(serverDest), { recursive: true });
fs.copyFileSync(dist, serverDest);

console.log('API client copied to', serverDest);
