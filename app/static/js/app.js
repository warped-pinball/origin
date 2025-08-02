const API_BASE = window.API_BASE || '';

function setTheme(theme) {
    const html = document.documentElement;
    html.dataset.theme = theme;
    const toggle = document.getElementById('theme-toggle');
    if (toggle) {
        toggle.checked = theme === 'dark';
    }
}

function toggleTheme() {
    const newTheme = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
    setTheme(newTheme);
    try {
        localStorage.setItem('theme', newTheme);
    } catch {}
}

function showToast(msg, type = 'info') {
    const toast = document.getElementById('toast');
    const icon = type === 'error' ? '❌' : type === 'success' ? '✅' : 'ℹ️';
    if (toast) {
        toast.textContent = `${icon} ${msg}`;
        toast.style.background = type === 'error' ? '#b91c1c' : type === 'success' ? '#15803d' : '#333';
        toast.style.zIndex = '2000';
        toast.style.display = 'block';
        setTimeout(() => toast.style.display = 'none', 3000);
    } else {
        alert(`${icon} ${msg}`);
    }
}

function logToFile(msg) {
    console.log(msg);
}

function isMobile() {
    return /Mobi|Android/i.test(navigator.userAgent) || window.innerWidth <= 768;
}

async function signup(e) {
    e.preventDefault();
    const phone = document.getElementById('signup-phone').value.trim();
    const password = document.getElementById('signup-password').value;
    const screen_name = document.getElementById('signup-screen').value;
    const btn = document.getElementById('signup-submit');
    const spinner = document.getElementById('signup-spinner');
    const errEl = document.getElementById('signup-error');
    if (errEl) errEl.textContent = '';
    if (spinner) spinner.style.display = 'inline-block';
    if (btn) btn.disabled = true;
    logToFile('Signup attempt: ' + phone);
    let res;
    try {
        res = await OriginApi.signup(phone, password, screen_name);
    } catch (err) {
        if (errEl) errEl.textContent = 'Network error';
        logToFile('Signup network error: ' + err);
        if (spinner) spinner.style.display = 'none';
        if (btn) btn.disabled = false;
        return;
    }
    if (res.ok) {
        let loginRes;
        try {
            loginRes = await OriginApi.login(phone, password);
        } catch (err) {
            logToFile('Auto-login error: ' + err);
            loginRes = { ok: false };
        }
        closeSignup();
        if (loginRes.ok) {
const data = await loginRes.json();
localStorage.setItem('token', data.access_token);
showLoggedIn();
showToast('Account created', 'success');
        } else if (loginRes.status === 403) {
showToast('Account created. Please verify using the SMS link before logging in.', 'info');
showLogin();
        } else {
showToast('Account created but login failed', 'error');
showLogin();
        }
    } else if (res.status === 422) {
        const phoneInput = document.getElementById('signup-phone');
        phoneInput.setCustomValidity('Please enter a valid phone number.');
        phoneInput.reportValidity();
    } else {
        showToast('Signup failed', 'error');
    }
    if (spinner) spinner.style.display = 'none';
    if (btn) btn.disabled = false;
}

async function login(e) {
    e.preventDefault();
    const phoneInput = document.getElementById('login-phone');
    const passwordInput = document.getElementById('login-password');
    const phone = phoneInput.value.trim();
    const password = passwordInput.value;
    phoneInput.setCustomValidity('');
    passwordInput.setCustomValidity('');
    document.getElementById('login-error').textContent = '';
    if(!/^\+?\d{10,15}$/.test(phone)) {
        phoneInput.setCustomValidity('Please enter a valid phone number.');
        phoneInput.reportValidity();
        return;
    }
    const res = await OriginApi.login(phone, password);
    if (res.ok) {
        const data = await res.json();
        localStorage.setItem('token', data.access_token);
        document.getElementById('login-error').textContent = '';
        showLoggedIn();
    } else if (res.status === 401 || res.status === 404) {
        document.getElementById('login-error').textContent = 'Invalid phone or password.';
    } else if (res.status === 403) {
        document.getElementById('login-error').textContent = 'Please verify your phone via the SMS link before logging in.';
    } else if (res.status >= 500) {
        showToast('Server error', 'error');
    } else {
        let msg = 'Login failed';
        try {
            const err = await res.json();
            if (err.detail) msg = err.detail;
        } catch {}
        document.getElementById('login-error').textContent = msg;
    }
}

function logout() {
    localStorage.removeItem('token');
    showLogin();
}

async function loadUserInfo() {
    const token = localStorage.getItem('token');
    if (!token) return;
    try {
        const res = await OriginApi.getMe(token);
        if (res.ok) {
            const user = await res.json();
            const screenInput = document.getElementById('account-screen');
            if (screenInput) screenInput.value = user.screen_name || '';
        }
    } catch {}
}

function highlightNav(id) {
    document.querySelectorAll('#navbar a[data-page]').forEach(link => {
        link.classList.add('secondary');
        link.classList.remove('primary');
    });
    const link = document.querySelector(`#navbar a[data-page="${id}"]`);
    if (link) {
        link.classList.add('primary');
        link.classList.remove('secondary');
    }
}

function displayPage(id) {
    document.querySelectorAll('.page').forEach(p => p.style.display = 'none');
    const el = document.getElementById(id);
    if (el) el.style.display = 'block';
    highlightNav(id);
}

function showPage(id, e) {
    if (e) e.preventDefault();
    if (location.hash !== '#' + id) {
        location.hash = id;
    } else {
        displayPage(id);
    }
}

async function updateScreenName(e) {
    e.preventDefault();
    const screen_name = document.getElementById('account-screen').value;
    const token = localStorage.getItem('token');
    const res = await OriginApi.updateScreenName(token, screen_name);
    const input = document.getElementById('account-screen');
    const actions = document.getElementById('account-actions');
    const btn = document.getElementById('account-save');
    if (res.ok) {
        showToast('Screen name updated', 'success');
        if (input) {
            input.value = screen_name;
            input.dataset.original = screen_name;
        }
        if (actions) actions.classList.remove('visible');
        if (btn) {
            const icon = btn.querySelector('.material-icons');
            const prev = icon ? icon.textContent : '';
            btn.classList.add('saved');
            if (icon) icon.textContent = 'check';
            setTimeout(() => {
                if (icon) icon.textContent = prev;
                btn.classList.remove('saved');
            }, 1000);
        }
    } else {
        showToast('Update failed', 'error');
    }
}

async function updatePassword(e) {
    e.preventDefault();
    const password = document.getElementById('account-password').value;
    const token = localStorage.getItem('token');
    const res = await OriginApi.updatePassword(token, password);
    if (res.ok) {
        showToast('Password changed', 'success');
        const dialog = document.getElementById('password-dialog');
        if (dialog) dialog.close();
    } else {
        showToast('Password change failed', 'error');
    }
}

function openDeleteConfirm() {
    const dialog = document.getElementById('delete-dialog');
    if (dialog) dialog.showModal();
}

async function deleteAccount() {
    const token = localStorage.getItem('token');
    const res = await OriginApi.deleteAccount(token);
    if (res.ok) {
        logout();
        showToast('Account deleted', 'success');
    } else {
        showToast('Delete failed', 'error');
    }
    const dialog = document.getElementById('delete-dialog');
    if (dialog) dialog.close();
}

function openSignup(e) {
    e.preventDefault();
    document.getElementById('signup-dialog').showModal();
}

function closeSignup() {
    document.getElementById('signup-dialog').close();
    const phoneInput = document.getElementById('signup-phone');
    if (phoneInput) {
        phoneInput.setCustomValidity('');
    }
    document.getElementById('signup-phone-error').textContent = '';
}

function showLogin() {
    const login = document.getElementById('login-section');
    const logged = document.getElementById('loggedin-section');
    if (login && logged) {
        login.style.display = 'block';
        logged.style.display = 'none';
        const err = document.getElementById('login-error');
        if (err) err.textContent = '';
        displayPage('');
        if (location.hash) history.replaceState(null, '', ' ');
        const title = document.getElementById('welcome-title');
        if (title) {
            title.textContent = 'Welcome';
            title.style.display = 'block';
        }
        const avatar = document.getElementById('profile-avatar');
        if (avatar) avatar.style.display = 'none';
    } else if (!location.pathname.endsWith('login.html')) {
        location.href = 'login.html';
    }
}

function showLoggedIn() {
    const login = document.getElementById('login-section');
    const logged = document.getElementById('loggedin-section');
    if (login && logged) {
        login.style.display = 'none';
        logged.style.display = 'block';
        const page = location.hash.substring(1) || 'achievements';
        displayPage(page);
        if (!location.hash) location.hash = page;
        loadUserInfo();
        const title = document.getElementById('welcome-title');
        if (title) {
            title.textContent = '';
            title.style.display = 'none';
        }
        const avatar = document.getElementById('profile-avatar');
        if (avatar) avatar.style.display = 'block';
    } else if (location.pathname.endsWith('login.html')) {
        location.href = 'index.html';
    }
}

function checkAuth() {
    const hasToken = !!localStorage.getItem('token');
    if (hasToken && location.pathname.endsWith('login.html')) {
        showLoggedIn();
    } else if (hasToken) {
        showLoggedIn();
    } else {
        showLogin();
    }
}

let deferredPrompt;
window.addEventListener('beforeinstallprompt', (e) => {
    if (!isMobile()) return;
    e.preventDefault();
    deferredPrompt = e;
    const dialog = document.getElementById('install-dialog');
    if (dialog && !dialog.open) dialog.showModal();
});

function installApp() {
    if (deferredPrompt) {
        deferredPrompt.prompt();
        deferredPrompt.userChoice.then(() => {
            deferredPrompt = null;
            const dialog = document.getElementById('install-dialog');
            if (dialog) dialog.close();
        });
    }
}

function closeInstall() {
    const dialog = document.getElementById('install-dialog');
    if (dialog) dialog.close();
}

document.addEventListener('DOMContentLoaded', () => {
    checkAuth();
    try {
        const storedTheme = localStorage.getItem('theme');
        if (storedTheme === 'light' || storedTheme === 'dark') {
            setTheme(storedTheme);
        }
    } catch {}
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/static/js/service-worker.js');
    }
    window.addEventListener('hashchange', () => {
        const page = location.hash.substring(1);
        if (page) displayPage(page);
    });
    const phoneInput = document.getElementById('signup-phone');
    if (phoneInput) {
        phoneInput.addEventListener('input', () => phoneInput.setCustomValidity(''));
    }
    const loginPhone = document.getElementById('login-phone');
    const loginPassword = document.getElementById('login-password');
    if (loginPhone) {
        loginPhone.addEventListener('input', () => loginPhone.setCustomValidity(''));
    }
    if (loginPassword) {
        loginPassword.addEventListener('input', () => loginPassword.setCustomValidity(''));
    }
    const themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
        themeToggle.checked = document.documentElement.dataset.theme === 'dark';
    }
    const confirmDelete = document.getElementById('confirm-delete-btn');
    if (confirmDelete) {
        confirmDelete.addEventListener('click', deleteAccount);
    }
    const avatar = document.getElementById('profile-avatar');
    const overlay = document.getElementById('account-overlay');
    const navbar = document.getElementById('navbar');
    const saveBtn = document.getElementById('account-save');
    const closeBtn = document.getElementById('account-close');
    const actions = document.getElementById('account-actions');
    const input = document.getElementById('account-screen');

    function closeOverlay() {
        if (overlay) {
            overlay.classList.remove('show');
        }
        if (input) {
            input.value = input.dataset.original || '';
        }
        if (actions) actions.classList.remove('visible');
        if (avatar) avatar.style.visibility = '';
        if (navbar) navbar.style.pointerEvents = '';
    }

    if (avatar && overlay) {
        avatar.addEventListener('click', () => {
            const r = avatar.getBoundingClientRect();
            overlay.style.setProperty('--clip-x', `${r.left + r.width / 2}px`);
            overlay.style.setProperty('--clip-y', `${r.top + r.height / 2}px`);
            if (navbar) navbar.style.pointerEvents = 'none';
            avatar.style.visibility = 'hidden';
            overlay.classList.add('show');
            if (input) {
                input.dataset.original = input.value;
                if (actions) actions.classList.remove('visible');
            }
        });
    }
    if (closeBtn) closeBtn.addEventListener('click', closeOverlay);
    if (input) {
        input.addEventListener('input', () => {
            if (actions) {
                if (input.value !== (input.dataset.original || '')) {
                    actions.classList.add('visible');
                } else {
                    actions.classList.remove('visible');
                }
            }
        });
    }
    if (saveBtn) saveBtn.addEventListener('click', updateScreenName);
    highlightNav(location.hash.substring(1) || 'achievements');
});

