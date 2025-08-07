(function (global) {
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
      } else if (loginRes.status === 403) {
        showToast('Account created. Please verify using the email link before logging in.', 'info');
        showLogin();
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
    } else if (res.status === 403) {
      document.getElementById('login-error').textContent = 'Please verify your email before logging in.';
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
    try {
      const res = await OriginApi.getMe();
      if (res.ok) {
        const user = await res.json();
        const screenInput = document.getElementById('account-screen');
        if (screenInput) screenInput.value = user.screen_name || '';
      }
    } catch {}
  }

  async function updateScreenName(e) {
    e.preventDefault();
    const screen_name = document.getElementById('account-screen').value;
    const res = await OriginApi.updateScreenName(screen_name);
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
    const res = await OriginApi.updatePassword(password);
    if (res.ok) {
      showToast('Password changed', 'success');
      const dialog = document.getElementById('password-dialog');
      if (dialog) dialog.close();
    } else {
      showToast('Password change failed', 'error');
    }
  }

  async function deleteAccount() {
    const res = await OriginApi.deleteAccount();
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

  global.signup = signup;
  global.login = login;
  global.logout = logout;
  global.loadUserInfo = loadUserInfo;
  global.updateScreenName = updateScreenName;
  global.updatePassword = updatePassword;
  global.deleteAccount = deleteAccount;
  global.openSignup = openSignup;
  global.closeSignup = closeSignup;
  global.showLogin = showLogin;
  global.showLoggedIn = showLoggedIn;
  global.checkAuth = checkAuth;
})(typeof window !== 'undefined' ? window : this);
