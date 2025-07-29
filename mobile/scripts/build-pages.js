const fs = require('fs');
const path = require('path');

const partials = {
  head: fs.readFileSync(path.join(__dirname, '../www/partials/head.html'), 'utf8'),
};

partials.nav = fs.readFileSync(path.join(__dirname, '../www/partials/nav.html'), 'utf8');

const pkg = require('../package.json');
const apiBase = process.env.PUBLIC_API_URL || require('../api-base');

const templateDir = path.join(__dirname, '../www/templates');
for (const file of fs.readdirSync(templateDir)) {
  if (!file.endsWith('.html')) continue;
  let content = fs.readFileSync(path.join(templateDir, file), 'utf8');
  content = content
    .replace('{{head}}', partials.head)
    .replace('{{nav}}', partials.nav)
    .replace(/{{version}}/g, pkg.version)
    .replace(/{{apiBase}}/g, apiBase);
  fs.writeFileSync(path.join(__dirname, '../www', file), content, 'utf8');
  console.log(`Built ${file}`);
}
