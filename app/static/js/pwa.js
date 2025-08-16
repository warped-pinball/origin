let deferredPrompt;

window.addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault();
  deferredPrompt = e;
  const banner = document.getElementById('install-banner');
  if (banner) {
    banner.hidden = false;
  }
});

window.addEventListener('appinstalled', () => {
  deferredPrompt = null;
  closeInstall();
});

function closeInstall() {
  const banner = document.getElementById('install-banner');
  if (banner) {
    banner.hidden = true;
  }
}

async function installApp() {
  if (!deferredPrompt) return;
  deferredPrompt.prompt();
  await deferredPrompt.userChoice;
  deferredPrompt = null;
  closeInstall();
}

window.closeInstall = closeInstall;
window.installApp = installApp;
