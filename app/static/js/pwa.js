let deferredPrompt;
const banner = document.getElementById('install-banner');

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

window.installApp = installApp;
window.closeInstall = hideInstall;
