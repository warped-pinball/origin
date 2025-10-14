let deferredPrompt;
const banner = document.getElementById('install-banner');
const installButton = document.getElementById('install-button');
const closeButton = document.getElementById('install-close-button');

function showInstall() {
  if (banner) {
    banner.hidden = false;
  }
}

function hideInstall() {
  if (banner) {
    banner.hidden = true;
  }
}

window.addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault();
  deferredPrompt = e;
  showInstall();
});

window.addEventListener('appinstalled', () => {
  deferredPrompt = null;
  hideInstall();
});

async function installApp() {
  if (!deferredPrompt) return;
  deferredPrompt.prompt();
  await deferredPrompt.userChoice;
  deferredPrompt = null;
  hideInstall();
}

if (installButton) {
  installButton.addEventListener('click', installApp);
}

if (closeButton) {
  closeButton.addEventListener('click', hideInstall);
}

window.installApp = installApp;
window.closeInstall = hideInstall;
