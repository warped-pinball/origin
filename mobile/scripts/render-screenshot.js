const puppeteer = require('puppeteer');
const path = require('path');
(async () => {
  const browser = await puppeteer.launch({ headless: 'new', args: ['--no-sandbox', '--disable-setuid-sandbox'] });
  const page = await browser.newPage();
  await page.emulateMediaFeatures([{ name: 'prefers-color-scheme', value: 'dark' }]);
  await page.setViewport({ width: 390, height: 844, deviceScaleFactor: 2 });

  const pages = ['splash', 'index', 'profile', 'achievements', 'shop', 'settings'];
  for (const name of pages) {
    const filePath = path.resolve(__dirname, `../www/${name}.html`);
    await page.goto('file://' + filePath, { waitUntil: 'networkidle0' });
    await page.screenshot({ path: path.resolve(__dirname, `../docs/screenshot-${name}.png`) });
    if (name === 'index') {
      // keep backward compatible screenshot
      await page.screenshot({ path: path.resolve(__dirname, '../docs/screenshot.png') });
    }
  }

  await browser.close();
})();
