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
      location.href = '/signup/success';
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

  global.signup = signup;
  document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('signup-form');
    if (form) form.addEventListener('submit', signup);
    const ret = document.getElementById('signup-return');
    if (ret) ret.addEventListener('click', () => location.href = '/');
  });
})(typeof window !== 'undefined' ? window : this);
