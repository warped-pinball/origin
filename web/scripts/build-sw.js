const path = require('node:path');
const workbox = require('workbox-build');

async function buildSW(staticDir = path.resolve(__dirname, '../../app/static')) {
  const { count, size, warnings } = await workbox.generateSW({
    swDest: path.join(staticDir, 'service-worker.js'),
    globDirectory: staticDir,
    globPatterns: ['**/*.{js,css,html,png,json}'],
    globIgnores: ['service-worker.js'],
    maximumFileSizeToCacheInBytes: 6 * 1024 * 1024,
    navigateFallback: '/static/offline.html',
    clientsClaim: true,
    skipWaiting: true,
    runtimeCaching: [
      {
        urlPattern: ({request}) => ['script','style','image'].includes(request.destination),
        handler: 'StaleWhileRevalidate',
        options: { cacheName: 'static-resources' }
      },
      {
        urlPattern: ({request}) => request.mode === 'navigate',
        handler: 'NetworkFirst',
        options: { cacheName: 'pages' }
      }
    ]
  });
  (warnings || []).forEach(w => console.warn(w));
  console.log(`Service worker built with ${count} files, ${size} bytes`);
}

if (require.main === module) {
  buildSW().catch(err => { console.error(err); process.exit(1); });
}

module.exports = buildSW;
