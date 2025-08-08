(function(global) {
  function getToken() {
    return new URLSearchParams(global.location.search).get('token');
  }

  async function requestReset(e) {
    e.preventDefault();
    const email = document.getElementById('reset-email').value.trim();
    const btn = document.getElementById('reset-submit');
    const spinner = document.getElementById('reset-spinner');
    const errEl = document.getElementById('reset-error');
    if (errEl) {
      errEl.textContent = '';
      errEl.style.color = 'red';
    }
    if (spinner) spinner.style.display = 'inline-block';
    if (btn) btn.disabled = true;
    let res;
    try {
      res = await OriginApi.requestPasswordReset(email);
    } catch (err) {
      if (errEl) errEl.textContent = 'Network error';
      if (spinner) spinner.style.display = 'none';
      if (btn) btn.disabled = false;
      return;
    }
    if (res.ok) {
      if (errEl) {
        errEl.style.color = 'green';
        errEl.textContent = 'If the email exists, a reset link has been sent.';
      }
    } else if (res.status === 422) {
      const emailInput = document.getElementById('reset-email');
      emailInput.setCustomValidity('Please enter a valid email address.');
      emailInput.reportValidity();
    } else {
      showToast('Request failed', 'error');
    }
    if (spinner) spinner.style.display = 'none';
    if (btn) btn.disabled = false;
  }

  async function resetPassword(e) {
    e.preventDefault();
    const password = document.getElementById('new-password').value.trim();
    const btn = document.getElementById('confirm-submit');
    const spinner = document.getElementById('confirm-spinner');
    const errEl = document.getElementById('confirm-error');
    if (errEl) {
      errEl.textContent = '';
      errEl.style.color = 'red';
    }
    if (spinner) spinner.style.display = 'inline-block';
    if (btn) btn.disabled = true;
    let res;
    try {
      res = await OriginApi.resetPassword(getToken(), password);
    } catch (err) {
      if (errEl) errEl.textContent = 'Network error';
      if (spinner) spinner.style.display = 'none';
      if (btn) btn.disabled = false;
      return;
    }
    if (res.ok) {
      if (errEl) {
        errEl.style.color = 'green';
        errEl.textContent = 'Password reset. Redirecting to login...';
      }
      showToast('Password reset. You can now log in.', 'success');
      setTimeout(() => { global.location.href = '/'; }, 1500);
    } else {
      showToast('Reset failed', 'error');
    }
    if (spinner) spinner.style.display = 'none';
    if (btn) btn.disabled = false;
  }

  function init() {
    if (getToken()) {
      const reqForm = document.getElementById('request-form');
      const resetForm = document.getElementById('reset-form');
      if (reqForm) reqForm.style.display = 'none';
      if (resetForm) resetForm.style.display = 'block';
    }
  }

  global.requestReset = requestReset;
  global.resetPassword = resetPassword;
  init();
})(typeof window !== 'undefined' ? window : this);
