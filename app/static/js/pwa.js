let deferredPrompt;

window.addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault();
  deferredPrompt = e;
  const dialog = document.getElementById('install-dialog');
  if (dialog) {
    dialog.showModal();
  }
});

window.addEventListener('appinstalled', () => {
  deferredPrompt = null;
  closeInstall();
});

function closeInstall() {
  const dialog = document.getElementById('install-dialog');
  if (dialog) {
    dialog.close();
  }
}

async function installApp() {
  if (!deferredPrompt) return;
  deferredPrompt.prompt();
  await deferredPrompt.userChoice;
  deferredPrompt = null;
  closeInstall();
}
