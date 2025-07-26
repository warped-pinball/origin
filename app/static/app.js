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
    toast.textContent = `${icon} ${msg}`;
    toast.style.background = type === 'error' ? '#b91c1c' : type === 'success' ? '#15803d' : '#333';
    toast.style.display = 'block';
    setTimeout(() => toast.style.display = 'none', 3000);
}

async function signup(e) {
    e.preventDefault();
    const email = document.getElementById('signup-email').value;
    const password = document.getElementById('signup-password').value;
    const screen_name = document.getElementById('signup-screen').value;
    const res = await fetch('/api/v1/users/', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({email, password, screen_name})
    });
    if (res.ok) {
        const loginRes = await fetch('/api/v1/auth/token', {
method: 'POST',
headers: {'Content-Type': 'application/x-www-form-urlencoded'},
body: new URLSearchParams({username: email, password})
        });
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
    const body = new URLSearchParams({username: email, password});
    const res = await fetch('/api/v1/auth/token', {
        method: 'POST',
        headers: {'Content-Type': 'application/x-www-form-urlencoded'},
        body
    });
    if (res.ok) {
        const data = await res.json();
        localStorage.setItem('token', data.access_token);
        document.getElementById('login-error').textContent = '';
        showLoggedIn();
    } else if (res.status === 404) {
        emailInput.setCustomValidity('User not found.');
        emailInput.reportValidity();
    } else if (res.status === 401) {
        passwordInput.setCustomValidity('Incorrect password.');
        passwordInput.reportValidity();
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

function showPage(id) {
    document.querySelectorAll('.page').forEach(p => p.style.display = 'none');
    const el = document.getElementById(id);
    if (el) el.style.display = 'block';
}

async function updateScreenName(e) {
    e.preventDefault();
    const screen_name = document.getElementById('account-screen').value;
    const token = localStorage.getItem('token');
    const res = await fetch('/api/v1/users/me', {
        method: 'PATCH',
        headers: {
'Content-Type': 'application/json',
'Authorization': 'Bearer ' + token
        },
        body: JSON.stringify({screen_name})
    });
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
    const res = await fetch('/api/v1/users/me/password', {
        method: 'POST',
        headers: {
'Content-Type': 'application/json',
'Authorization': 'Bearer ' + token
        },
        body: JSON.stringify({password})
    });
    if (res.ok) {
        showToast('Password changed', 'success');
    } else {
        showToast('Password change failed', 'error');
    }
}

async function deleteAccount() {
    if(!confirm('Are you sure you want to delete your account?')) return;
    const token = localStorage.getItem('token');
    const res = await fetch('/api/v1/users/me', {
        method: 'DELETE',
        headers: {'Authorization': 'Bearer ' + token}
    });
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
    document.getElementById('login-section').style.display = 'block';
    document.getElementById('loggedin-section').style.display = 'none';
    document.getElementById('login-error').textContent = '';
    showPage('landing');
    document.getElementById('logout-btn').style.display = 'none';
}

function showLoggedIn() {
    document.getElementById('login-section').style.display = 'none';
    document.getElementById('loggedin-section').style.display = 'block';
    showPage('landing');
    document.getElementById('logout-btn').style.display = 'flex';
}

function checkAuth() {
    localStorage.getItem('token') ? showLoggedIn() : showLogin();
}

document.addEventListener('DOMContentLoaded', () => {
    checkAuth();
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

