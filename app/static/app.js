const API_BASE = window.API_BASE || '';

function toggleTheme() {
    const html = document.documentElement;
    const newTheme = html.dataset.theme === 'dark' ? 'light' : 'dark';
    html.dataset.theme = newTheme;
    const toggle = document.getElementById('theme-toggle');
    if (toggle) {
        toggle.checked = newTheme === 'dark';
    }
}

function showToast(msg, type = 'info') {
    const toast = document.getElementById('toast');
    const icon = type === 'error' ? '❌' : type === 'success' ? '✅' : 'ℹ️';
    if (toast) {
        toast.textContent = `${icon} ${msg}`;
        toast.style.background = type === 'error' ? '#b91c1c' : type === 'success' ? '#15803d' : '#333';
        toast.style.display = 'block';
        setTimeout(() => toast.style.display = 'none', 3000);
    } else {
        alert(`${icon} ${msg}`);
    }
}

function logToFile(msg) {
    console.log(msg);
}

async function signup(e) {
    e.preventDefault();
    const email = document.getElementById('signup-email').value.trim();
    const password = document.getElementById('signup-password').value;
    const screen_name = document.getElementById('signup-screen').value;
    const btn = document.getElementById('signup-submit');
    const spinner = document.getElementById('signup-spinner');
    const errEl = document.getElementById('signup-error');
    if (errEl) errEl.textContent = '';
    if (spinner) spinner.style.display = 'inline-block';
    if (btn) btn.disabled = true;
    logToFile('Signup attempt: ' + email);
    let res;
    try {
        res = await OriginApi.signup(email, password, screen_name);
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
            loginRes = await OriginApi.login(email, password);
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
        } else {
showToast('Account created but login failed', 'error');
showLogin();
        }
    } else if (res.status === 422) {
        const emailInput = document.getElementById('signup-email');
        emailInput.setCustomValidity('Please enter a valid email address.');
        emailInput.reportValidity();
    } else {
        showToast('Signup failed', 'error');
    }
    if (spinner) spinner.style.display = 'none';
    if (btn) btn.disabled = false;
}

async function login(e) {
    e.preventDefault();
    const emailInput = document.getElementById('login-email');
    const passwordInput = document.getElementById('login-password');
    const email = emailInput.value.trim();
    const password = passwordInput.value;
    emailInput.setCustomValidity('');
    passwordInput.setCustomValidity('');
    document.getElementById('login-error').textContent = '';
    if(!/^\S+@\S+\.\S+$/.test(email)) {
        emailInput.setCustomValidity('Please enter a valid email address.');
        emailInput.reportValidity();
        return;
    }
    const res = await OriginApi.login(email, password);
    if (res.ok) {
        const data = await res.json();
        localStorage.setItem('token', data.access_token);
        document.getElementById('login-error').textContent = '';
        showLoggedIn();
    } else if (res.status === 401 || res.status === 404) {
        document.getElementById('login-error').textContent = 'Invalid email or password.';
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

function moveIndicator(id) {
    const indicator = document.getElementById('nav-indicator');
    const item = document.querySelector(`#navbar li[data-page="${id}"]`);
    if (indicator && item) {
        const offset = item.offsetLeft + item.offsetWidth / 2 - indicator.offsetWidth / 2;
        indicator.style.transform = `translateX(${offset}px)`;
    }
}

function displayPage(id) {
    document.querySelectorAll('.page').forEach(p => p.style.display = 'none');
    const el = document.getElementById(id);
    if (el) el.style.display = 'block';
    moveIndicator(id);
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
    if (res.ok) {
        showToast('Screen name updated', 'success');
        const avatarInput = document.getElementById('account-screen');
        if (avatarInput) avatarInput.value = screen_name;
        const overlay = document.getElementById('account-overlay');
        if (overlay) {
            overlay.classList.remove('show');
            overlay.style.display = 'none';
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
    const emailInput = document.getElementById('signup-email');
    if (emailInput) {
        emailInput.setCustomValidity('');
    }
    document.getElementById('signup-email-error').textContent = '';
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
    e.preventDefault();
    deferredPrompt = e;
    const btn = document.getElementById('install-btn');
    if (btn) btn.style.display = 'block';
});

function installApp() {
    if (deferredPrompt) {
        deferredPrompt.prompt();
        deferredPrompt.userChoice.then(() => {
            deferredPrompt = null;
            const btn = document.getElementById('install-btn');
            if (btn) btn.style.display = 'none';
        });
    }
}

document.addEventListener('DOMContentLoaded', () => {
    checkAuth();
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/static/service-worker.js');
    }
    window.addEventListener('hashchange', () => {
        const page = location.hash.substring(1);
        if (page) displayPage(page);
    });
    const emailInput = document.getElementById('signup-email');
    if (emailInput) {
        emailInput.addEventListener('input', () => emailInput.setCustomValidity(''));
    }
    const loginEmail = document.getElementById('login-email');
    const loginPassword = document.getElementById('login-password');
    if (loginEmail) {
        loginEmail.addEventListener('input', () => loginEmail.setCustomValidity(''));
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
    const saveBtn = document.getElementById('account-save');
    const input = document.getElementById('account-screen');
    if (avatar && overlay) {
        avatar.addEventListener('click', () => {
            overlay.style.display = 'block';
            overlay.classList.add('show');
            if (input) input.focus();
        });
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                overlay.classList.remove('show');
                overlay.style.display = 'none';
            }
        });
    }
    if (input && saveBtn) {
        input.addEventListener('input', () => saveBtn.style.display = 'inline-block');
        saveBtn.addEventListener('click', updateScreenName);
    }
    moveIndicator(location.hash.substring(1) || 'achievements');
});

