(function (global) {
  let tournamentFilter = 'all';

  function applyTournamentFilter() {
    const now = new Date();
    const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    let end = null;
    if (tournamentFilter === 'today') {
      end = new Date(startOfToday);
      end.setDate(end.getDate() + 1);
    } else if (tournamentFilter === 'next7') {
      end = new Date(now);
      end.setDate(end.getDate() + 7);
    } else if (tournamentFilter === 'next30') {
      end = new Date(now);
      end.setDate(end.getDate() + 30);
    }
    document.querySelectorAll('#owned-tournaments li, #joined-tournaments-list li, #public-tournaments-list li').forEach(li => {
      const start = new Date(li.dataset.start);
      let visible;
      if (!end) {
        visible = true;
      } else if (tournamentFilter === 'today') {
        visible = start >= startOfToday && start < end;
      } else {
        visible = start >= now && start < end;
      }
      li.style.display = visible ? '' : 'none';
    });
  }

  function setTournamentFilter(filter) {
    tournamentFilter = filter;
    document.querySelectorAll('.tournament-filter-btn').forEach(btn => {
      const active = btn.dataset.range === filter;
      btn.classList.toggle('primary', active);
      btn.classList.toggle('secondary', !active);
    });
    applyTournamentFilter();
  }

  async function createTournament(e) {
    e.preventDefault();
    const body = {
      name: document.getElementById('tournament-name').value,
      start_time: document.getElementById('tournament-start').value,
      rule_set: document.getElementById('tournament-rules').value,
      public: document.getElementById('tournament-public').checked,
      allow_invites: document.getElementById('tournament-invites').checked
    };
    const res = await apiFetch('/api/v1/tournaments/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
    if (res.ok) {
      const t = await res.json();
      addTournamentToList(t, 'owned-tournaments');
      showToast('Tournament created', 'success');
      showTournamentView(t);
    } else {
      showToast('Failed to create tournament', 'error');
    }
  }

  function addTournamentToList(t, listId) {
    const ul = document.getElementById(listId);
    if (!ul) return;
    const li = document.createElement('li');
    li.textContent = `${t.name} - ${new Date(t.start_time).toLocaleString()}`;
    li.dataset.start = t.start_time;
    if (t.owner_id === 1) {
      const manageBtn = document.createElement('button');
      manageBtn.textContent = 'Manage';
      manageBtn.addEventListener('click', () => showTournamentManagementById(t.id));
      li.appendChild(manageBtn);
    }
    if (listId === 'joined-tournaments-list' && t.allow_invites) {
      const shareBtn = document.createElement('button');
      shareBtn.textContent = 'Invite Players';
      shareBtn.addEventListener('click', () => shareTournament(t));
      li.appendChild(shareBtn);
    }
    ul.appendChild(li);
    applyTournamentFilter();
  }

  async function showTournamentManagementById(id) {
    const res = await apiFetch(`/api/v1/tournaments/${id}`);
    if (res.ok) {
      const t = await res.json();
      showTournamentManagement(t);
    }
  }

  async function updateAllowInvites(id, allow) {
    await apiFetch(`/api/v1/tournaments/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ allow_invites: allow })
    });
  }

  function showTournamentManagement(t) {
    const nameEl = document.getElementById('tournament-manage-name');
    if (nameEl) nameEl.textContent = `${t.name} - ${new Date(t.start_time).toLocaleString()}`;
    const allowInput = document.getElementById('allow-invites');
    if (allowInput) {
      allowInput.checked = t.allow_invites;
      allowInput.onchange = async () => {
        await updateAllowInvites(t.id, allowInput.checked);
        t.allow_invites = allowInput.checked;
        const shareBtn = document.getElementById('share-tournament');
        if (shareBtn) shareBtn.style.display = t.allow_invites ? 'block' : 'none';
      };
    }
    const regUl = document.getElementById('registered-users');
    if (regUl) {
      regUl.innerHTML = '';
      t.registered_users.forEach(u => {
        const li = document.createElement('li');
        li.textContent = `User ${u}`;
        regUl.appendChild(li);
      });
    }
    const joinUl = document.getElementById('joined-users');
    if (joinUl) {
      joinUl.innerHTML = '';
      t.joined_users.forEach(u => {
        const li = document.createElement('li');
        li.textContent = `User ${u}`;
        joinUl.appendChild(li);
      });
    }
    const shareBtn = document.getElementById('share-tournament');
    if (shareBtn) {
      shareBtn.style.display = t.allow_invites ? 'block' : 'none';
      shareBtn.onclick = () => shareTournament(t);
    }
    showPage('tournament-manage');
  }

  function shareTournament(t) {
    const link = `${window.location.origin}/?tournament=${t.id}`;
    const baseText = `Join my tournament ${t.name} on ${new Date(t.start_time).toLocaleString()}.`;
    if (navigator.share) {
      navigator.share({ text: baseText, url: link });
    } else if (navigator.clipboard) {
      const msg = `${baseText}\nOpen this link to view and join: ${link}`;
      navigator.clipboard.writeText(msg);
      showToast('Invitation copied', 'info');
    } else {
      showToast('Sharing not supported', 'error');
    }
  }

  async function joinTournament(id) {
    const res = await apiFetch(`/api/v1/tournaments/${id}/join`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: 1 })
    });
    if (res.ok) {
      showToast('Joined tournament', 'success');
    } else {
      showToast('Failed to join', 'error');
    }
  }

  function showTournamentView(t) {
    const nameEl = document.getElementById('tournament-view-name');
    if (nameEl) nameEl.textContent = `${t.name}`;
    const startEl = document.getElementById('tournament-view-start');
    if (startEl) startEl.textContent = new Date(t.start_time).toLocaleString();
    const actionBtn = document.getElementById('tournament-view-action');
    if (actionBtn) {
      if (t.owner_id === 1) {
        actionBtn.textContent = 'Invite Players';
        actionBtn.onclick = () => shareTournament(t);
      } else {
        actionBtn.textContent = 'Join Tournament';
        actionBtn.onclick = () => joinTournament(t.id);
      }
    }
    history.replaceState(null, '', `?tournament=${t.id}`);
    showPage('tournament-view');
  }

  async function showTournamentViewById(id) {
    const res = await apiFetch(`/api/v1/tournaments/${id}`);
    if (res.ok) {
      const t = await res.json();
      showTournamentView(t);
    }
  }

  global.setTournamentFilter = setTournamentFilter;
  global.createTournament = createTournament;
  global.addTournamentToList = addTournamentToList;
  global.showTournamentManagementById = showTournamentManagementById;
  global.updateAllowInvites = updateAllowInvites;
  global.showTournamentManagement = showTournamentManagement;
  global.shareTournament = shareTournament;
  global.joinTournament = joinTournament;
  global.showTournamentView = showTournamentView;
  global.showTournamentViewById = showTournamentViewById;
  global.applyTournamentFilter = applyTournamentFilter;
})(typeof window !== 'undefined' ? window : this);
