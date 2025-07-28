const API_BASE = window.API_BASE || '';

function toggleTheme() {
    const html = document.documentElement;
    const newTheme = html.dataset.theme === 'dark' ? 'light' : 'dark';
    html.dataset.theme = newTheme;
    const icon = document.getElementById('theme-icon');
    if (icon) {
        icon.textContent = newTheme === 'dark' ? 'light_mode' : 'dark_mode';
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

async function signup(e) {
    e.preventDefault();
    const email = document.getElementById('signup-email').value;
    const password = document.getElementById('signup-password').value;
    const screen_name = document.getElementById('signup-screen').value;
    const res = await OriginApi.signup(email, password, screen_name);
    if (res.ok) {
        const loginRes = await OriginApi.login(email, password);
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
}

async function login(e) {
    e.preventDefault();
    const emailInput = document.getElementById('login-email');
    const passwordInput = document.getElementById('login-password');
    const email = emailInput.value;
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

function displayPage(id) {
    document.querySelectorAll('.page').forEach(p => p.style.display = 'none');
    const el = document.getElementById(id);
    if (el) el.style.display = 'block';
}

function showPage(id) {
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
    } else {
        showToast('Password change failed', 'error');
    }
}

async function deleteAccount() {
    if(!confirm('Are you sure you want to delete your account?')) return;
    const token = localStorage.getItem('token');
    const res = await OriginApi.deleteAccount(token);
    if (res.ok) {
        logout();
        showToast('Account deleted', 'success');
    } else {
        showToast('Delete failed', 'error');
    }
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
        const btn = document.getElementById('logout-btn');
        if (btn) btn.style.display = 'none';
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
        const btn = document.getElementById('logout-btn');
        if (btn) btn.style.display = 'flex';
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

document.addEventListener('DOMContentLoaded', () => {
    checkAuth();
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
});

