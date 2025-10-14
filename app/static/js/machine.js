(function (global) {
  const config = global.machineConfig || {};
  const machineId = config.id;
  const toastEl = document.getElementById('toast');
  const qrLinkEl = document.getElementById('machine-qr-link');
  const copyLinkBtn = document.getElementById('copy-machine-link');
  const openLinkEl = document.getElementById('open-machine-link');
  const scoreboardList = document.getElementById('scoreboard-list');
  const scoreboardEmpty = document.getElementById('scoreboard-empty');
  const scoreboardUpdated = document.getElementById('scoreboard-updated');
  const refreshBtn = document.getElementById('refresh-scores');
  const toggleBtn = document.getElementById('toggle-select');
  const claimSection = document.getElementById('claim-section');
  const claimForm = document.getElementById('claim-form');
  const claimOptions = document.getElementById('claim-options');

  let latestState = null;
  let selecting = false;

  function showToast(message, type = 'info') {
    if (!toastEl) return;
    const icon = type === 'error' ? '❌' : type === 'success' ? '✅' : 'ℹ️';
    toastEl.textContent = `${icon} ${message}`;
    toastEl.style.background = type === 'error' ? '#b91c1c' : type === 'success' ? '#15803d' : '#333';
    toastEl.style.display = 'block';
    setTimeout(() => {
      toastEl.style.display = 'none';
    }, 3000);
  }

  function getQrLink() {
    const links = Array.isArray(config.qr_links) ? config.qr_links : [];
    return links[0] || '';
  }

  function renderQrLink() {
    const link = getQrLink();
    if (qrLinkEl) {
      qrLinkEl.textContent = link || 'No QR code has been assigned to this machine yet.';
    }
    if (copyLinkBtn) {
      copyLinkBtn.disabled = !link;
      copyLinkBtn.style.display = link ? 'inline-flex' : 'none';
    }
    if (openLinkEl) {
      if (link) {
        openLinkEl.href = link;
        openLinkEl.style.display = 'inline-flex';
      } else {
        openLinkEl.removeAttribute('href');
        openLinkEl.style.display = 'none';
      }
    }
  }

  function formatNumber(value) {
    try {
      return Number(value || 0).toLocaleString();
    } catch (err) {
      return String(value || 0);
    }
  }

  function formatTimestamp(iso) {
    if (!iso) return '';
    try {
      const date = new Date(iso);
      if (Number.isNaN(date.getTime())) return '';
      return date.toLocaleString();
    } catch (err) {
      return '';
    }
  }

  function renderClaimOptions(state) {
    if (!claimOptions) return;
    claimOptions.innerHTML = '';
    const scores = Array.isArray(state.scores) ? state.scores : [];
    scores.forEach((score, index) => {
      const wrapper = document.createElement('div');
      wrapper.className = 'claim-option';

      const label = document.createElement('label');
      label.htmlFor = `claim-player-${index}`;
      const title = document.createElement('strong');
      title.textContent = `Player ${index + 1}`;
      label.appendChild(title);

      const scoreSpan = document.createElement('span');
      scoreSpan.textContent = score == null ? 'No score reported yet' : `${formatNumber(score)} points`;
      label.appendChild(scoreSpan);

      if (state.player_up === index) {
        const active = document.createElement('span');
        active.textContent = 'Up now';
        active.style.color = 'var(--pico-primary,#2563eb)';
        label.appendChild(active);
      }

      const checkbox = document.createElement('input');
      checkbox.type = 'checkbox';
      checkbox.id = `claim-player-${index}`;
      checkbox.name = 'players';
      checkbox.value = String(index);

      wrapper.appendChild(label);
      wrapper.appendChild(checkbox);
      claimOptions.appendChild(wrapper);
    });
  }

  function renderScores(state) {
    if (!scoreboardList) return;
    scoreboardList.innerHTML = '';
    const scores = Array.isArray(state.scores) ? state.scores : [];
    if (!scores.length) {
      if (scoreboardEmpty) scoreboardEmpty.style.display = 'block';
      if (toggleBtn) toggleBtn.style.display = 'none';
      if (claimSection) claimSection.style.display = 'none';
      return;
    }

    if (scoreboardEmpty) scoreboardEmpty.style.display = 'none';
    if (toggleBtn) toggleBtn.style.display = 'inline-flex';

    scores.forEach((score, index) => {
      const item = document.createElement('li');
      item.className = 'machine-score-item';

      const label = document.createElement('strong');
      label.textContent = `Player ${index + 1}`;
      item.appendChild(label);

      const meta = document.createElement('div');
      meta.className = 'machine-score-meta';

      const scoreSpan = document.createElement('span');
      scoreSpan.textContent = score == null ? 'No score yet' : `${formatNumber(score)} pts`;
      meta.appendChild(scoreSpan);

      if (state.player_up === index) {
        const active = document.createElement('span');
        active.textContent = 'Currently up';
        meta.appendChild(active);
      }

      if (state.players_total) {
        const total = document.createElement('span');
        total.textContent = `${state.players_total} player${state.players_total === 1 ? '' : 's'}`;
        meta.appendChild(total);
      }

      item.appendChild(meta);
      scoreboardList.appendChild(item);
    });

    if (scoreboardUpdated) {
      const stamp = formatTimestamp(state.created_at);
      if (stamp) {
        scoreboardUpdated.style.display = 'block';
        scoreboardUpdated.textContent = `Updated ${stamp}`;
      } else {
        scoreboardUpdated.style.display = 'none';
      }
    }

    renderClaimOptions(state);
  }

  async function loadScores(showToastOnError = true) {
    if (!machineId) return;
    try {
      const res = await OriginApi.getMachineState(machineId);
      if (!res.ok) {
        if (showToastOnError) showToast('Unable to load scores', 'error');
        return;
      }
      latestState = await res.json();
      renderScores(latestState);
    } catch (err) {
      if (showToastOnError) showToast('Unable to load scores', 'error');
    }
  }

  async function claimScores(event) {
    if (event && typeof event.preventDefault === 'function') event.preventDefault();
    if (!machineId) return;
    if (!latestState) {
      showToast('No scores are available to claim yet', 'error');
      return;
    }
    const selected = Array.from(claimForm.querySelectorAll('input[name="players"]:checked'))
      .map(input => Number.parseInt(input.value, 10))
      .filter(index => Number.isInteger(index));
    if (!selected.length) {
      showToast('Select at least one player to continue', 'error');
      return;
    }
    try {
      const res = await OriginApi.claimMachineScores(machineId, selected);
      if (!res.ok) {
        let detail = 'Unable to record scores';
        try {
          const err = await res.json();
          if (err && err.detail) detail = err.detail;
        } catch (innerErr) {}
        showToast(detail, 'error');
        return;
      }
      const payload = await res.json();
      const recorded = payload && typeof payload.recorded === 'number' ? payload.recorded : selected.length;
      showToast(`Recorded ${recorded} score${recorded === 1 ? '' : 's'}`, 'success');
      selecting = false;
      if (claimSection) claimSection.style.display = 'none';
      if (toggleBtn) toggleBtn.textContent = 'Select players';
      await loadScores(false);
    } catch (err) {
      showToast('Unable to record scores', 'error');
    }
  }

  function toggleSelection() {
    selecting = !selecting;
    if (selecting) {
      if (claimSection) claimSection.style.display = 'block';
      if (toggleBtn) toggleBtn.textContent = 'Hide selection';
    } else {
      if (claimSection) claimSection.style.display = 'none';
      if (toggleBtn) toggleBtn.textContent = 'Select players';
      if (claimForm) {
        claimForm.reset();
      }
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    renderQrLink();
    loadScores();

    if (copyLinkBtn) {
      copyLinkBtn.addEventListener('click', async e => {
        if (e && typeof e.preventDefault === 'function') e.preventDefault();
        const link = getQrLink();
        if (!link) return;
        try {
          if (
            global.navigator &&
            global.navigator.clipboard &&
            typeof global.navigator.clipboard.writeText === 'function'
          ) {
            await global.navigator.clipboard.writeText(link);
            showToast('Machine link copied', 'success');
          } else {
            throw new Error('Clipboard unavailable');
          }
        } catch (err) {
          showToast('Unable to copy link', 'error');
        }
      });
    }

    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => loadScores());
    }

    if (toggleBtn) {
      toggleBtn.addEventListener('click', toggleSelection);
    }

    if (claimForm) {
      claimForm.addEventListener('submit', claimScores);
    }
  });
})(typeof window !== 'undefined' ? window : this);
