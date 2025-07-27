const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');

function getNavLinks(pageName) {
  const filePath = path.join('www', `${pageName}.html`);
  const html = fs.readFileSync(filePath, 'utf8');
  const navMatch = html.match(/<nav class="bottom-nav">([\s\S]*?)<\/nav>/);
  assert(navMatch, `no nav menu in ${filePath}`);
  const links = [];
  const re = /href="([^"]+)"/g;
  let m;
  while ((m = re.exec(navMatch[1])) !== null) {
    links.push(m[1]);
  }
  return links;
}

test('navigation menu is populated on each page', () => {
  const pages = ['index', 'profile', 'achievements', 'shop', 'settings'];
  for (const name of pages) {
    const links = getNavLinks(name);
    assert.deepStrictEqual(links, [
      'profile.html',
      'achievements.html',
      'index.html',
      'shop.html',
      'settings.html'
    ]);
  }
});
