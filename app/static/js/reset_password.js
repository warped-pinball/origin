(function(global) {
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

  global.requestReset = requestReset;
})(typeof window !== 'undefined' ? window : this);
