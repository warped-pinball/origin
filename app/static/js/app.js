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
    const params = new URLSearchParams(location.search);
    const tId = params.get('tournament');
    if (tId) {
        showTournamentViewById(tId);
    }
    document.querySelectorAll('.tournament-filter-btn').forEach(btn => {
        btn.addEventListener('click', () => setTournamentFilter(btn.dataset.range));
    });
    setTournamentFilter('all');
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
    const tournamentForm = document.getElementById('tournament-form');
    if (tournamentForm) {
        tournamentForm.addEventListener('submit', createTournament);
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
