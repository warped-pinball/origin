(function (global) {
  let cachedLocations = [];
  let cachedMachines = [];
  let cachedQrCodes = [];
  let currentLocationId = null;
  let currentLocation = null;
  let claimedMachineId = null;

  function getLocationDashboardUrl(loc) {
    if (!loc || !loc.id) return '';
    const { origin, protocol, host } = global.location || {};
    const base = origin || (protocol && host ? `${protocol}//${host}` : '');
    const trimmed = base ? base.replace(/\/$/, '') : '';
    const prefix = trimmed || '';
    return (prefix ? prefix : '') + '/locations/' + loc.id + '/display';
  }

  function createQrInfo(qr) {
    const info = document.createElement('div');
    info.className = 'machine-qr-info';

    const link = document.createElement('a');
    link.href = qr.url;
    link.textContent = qr.url;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    info.appendChild(link);

    if (qr.code) {
      const codeLabel = document.createElement('span');
      codeLabel.className = 'machine-qr-code';
      codeLabel.textContent = `Code: ${qr.code}`;
      info.appendChild(codeLabel);
    }

    return info;
  }

  function createQrActions(qr) {
    const actions = document.createElement('div');
    actions.className = 'machine-qr-actions';

    const copyBtn = document.createElement('button');
    copyBtn.type = 'button';
    copyBtn.className = 'secondary outline';
    copyBtn.textContent = 'Copy link';
    copyBtn.onclick = async e => {
      if (e && typeof e.preventDefault === 'function') e.preventDefault();
      try {
        if (
          global.navigator &&
          global.navigator.clipboard &&
          typeof global.navigator.clipboard.writeText === 'function'
        ) {
          await global.navigator.clipboard.writeText(qr.url);
          showToast('QR link copied', 'success');
        } else {
          throw new Error('Clipboard unavailable');
        }
      } catch (err) {
        showToast('Unable to copy QR link', 'error');
      }
    };

    const openLink = document.createElement('a');
    openLink.href = qr.url;
    openLink.target = '_blank';
    openLink.rel = 'noopener noreferrer';
    openLink.className = 'secondary outline';
    openLink.textContent = 'Open';

    actions.appendChild(copyBtn);
    actions.appendChild(openLink);

    return actions;
  }

  function createMachineQrEntry(qr) {
    const item = document.createElement('li');
    item.className = 'machine-qr-entry';
    item.appendChild(createQrInfo(qr));
    item.appendChild(createQrActions(qr));
    return item;
  }

  function updateLocationDashboard(loc) {
    const container = document.getElementById('location-dashboard');
    const linkEl = document.getElementById('location-dashboard-link');
    const copyBtn = document.getElementById('location-dashboard-copy');
    const openBtn = document.getElementById('location-dashboard-open');
    const shareBtn = document.getElementById('location-dashboard-share');
    if (!container) return;
    if (!loc || !loc.id) {
      container.style.display = 'none';
      if (linkEl) {
        linkEl.textContent = '';
        linkEl.removeAttribute('href');
      }
      if (copyBtn) copyBtn.onclick = null;
      if (openBtn) openBtn.onclick = null;
      if (shareBtn) {
        shareBtn.style.display = 'none';
        shareBtn.onclick = null;
      }
      return;
    }
    const url = getLocationDashboardUrl(loc);
    if (linkEl) {
      linkEl.href = url;
      linkEl.textContent = url;
      linkEl.target = '_blank';
      linkEl.rel = 'noopener noreferrer';
    }
    if (openBtn) {
      openBtn.onclick = e => {
        if (e && typeof e.preventDefault === 'function') e.preventDefault();
        if (typeof global.open === 'function') {
          global.open(url, '_blank', 'noopener');
        } else if (global.window && typeof global.window.open === 'function') {
          global.window.open(url, '_blank', 'noopener');
        }
      };
    }
    if (copyBtn) {
      copyBtn.onclick = async e => {
        if (e && typeof e.preventDefault === 'function') e.preventDefault();
        try {
          if (global.navigator && global.navigator.clipboard && typeof global.navigator.clipboard.writeText === 'function') {
            await global.navigator.clipboard.writeText(url);
            showToast('Location link copied', 'success');
          } else {
            throw new Error('Clipboard unavailable');
          }
        } catch (error) {
          showToast('Unable to copy link', 'error');
        }
      };
    }
    if (shareBtn) {
      if (global.navigator && typeof global.navigator.share === 'function') {
        shareBtn.style.display = 'inline-flex';
        shareBtn.onclick = async e => {
          if (e && typeof e.preventDefault === 'function') e.preventDefault();
          try {
            await global.navigator.share({
              title: loc.name ? `${loc.name} on Origin` : 'Location dashboard',
              text: loc.name ? `Check out ${loc.name} on Origin.` : 'Check out this location on Origin.',
              url
            });
          } catch (err) {
            if (!err || err.name !== 'AbortError') {
              showToast('Unable to share link', 'error');
            }
          }
        };
      } else {
        shareBtn.style.display = 'none';
        shareBtn.onclick = null;
      }
    }
    container.style.display = 'block';
  }

  function getMachineLabel(machine) {
    return machine.name || machine.game_title || machine.id || 'Machine';
  }

  async function loadLocations() {
    try {
      const res = await OriginApi.getLocations();
      if (!res.ok) return;
      cachedLocations = await res.json();
      const list = document.getElementById('locations-list');
      if (list) {
        list.innerHTML = '';
        cachedLocations.forEach(loc => {
          const card = document.createElement('article');
          const title = document.createElement('h4');
          title.textContent = loc.name;
          card.appendChild(title);
          if (loc.address) {
            const p = document.createElement('p');
            p.textContent = loc.address;
            card.appendChild(p);
          }
          card.style.cursor = 'pointer';
          card.onclick = () => openLocation(loc);
          list.appendChild(card);
        });
      }
      renderMachineOptions();
    } catch (error) {}
  }

  function renderMachineOptions() {
    document.querySelectorAll('.machine-location').forEach(sel => {
      const machineId = sel.dataset.machine;
      sel.innerHTML = '<option value="">Select location</option>';
      cachedLocations.forEach(loc => {
        const opt = document.createElement('option');
        opt.value = loc.id;
        opt.textContent = loc.name;
        if (String(sel.dataset.selected) === String(loc.id)) opt.selected = true;
        sel.appendChild(opt);
      });
      sel.onchange = () => {
        if (sel.value) assignMachine(machineId, sel.value);
      };
    });
  }

  async function loadMachines() {
    try {
      const res = await OriginApi.getMachines();
      if (!res.ok) return;
      const machines = await res.json();
      cachedMachines = machines;
      const list = document.getElementById('machines-list');
      const help = document.getElementById('machine-setup-message');
      let highlighted = false;
      if (list) {
        list.innerHTML = '';
        machines.forEach(m => {
          const li = document.createElement('li');
          li.className = 'machine-item';

          const nameSpan = document.createElement('span');
          nameSpan.className = 'machine-label';
          nameSpan.textContent = getMachineLabel(m);
          li.appendChild(nameSpan);

          const controls = document.createElement('div');
          controls.className = 'machine-controls';

          const sel = document.createElement('select');
          sel.className = 'machine-location';
          sel.dataset.machine = m.id;
          sel.dataset.selected = m.location_id || '';
          controls.appendChild(sel);

          const removeBtn = document.createElement('button');
          removeBtn.type = 'button';
          removeBtn.className = 'secondary outline machine-remove';
          removeBtn.textContent = 'Unregister';
          removeBtn.onclick = () => unregisterMachine(m.id);
          controls.appendChild(removeBtn);

          li.appendChild(controls);

          const qrSection = document.createElement('div');
          qrSection.className = 'machine-qr-section';
          const codes = Array.isArray(m.qr_codes) ? m.qr_codes : [];
          if (codes.length) {
            const qrTitle = document.createElement('p');
            qrTitle.className = 'machine-qr-title';
            qrTitle.textContent = codes.length === 1 ? 'QR code' : 'QR codes';
            qrSection.appendChild(qrTitle);

            const qrList = document.createElement('ul');
            qrList.className = 'machine-qr-list';

            codes.forEach(qr => {
              qrList.appendChild(createMachineQrEntry(qr));
            });

            qrSection.appendChild(qrList);
          } else {
            const empty = document.createElement('p');
            empty.className = 'machine-qr-empty';
            empty.textContent = 'No QR codes have been assigned yet.';
            qrSection.appendChild(empty);
          }

          li.appendChild(qrSection);
          list.appendChild(li);

          if (claimedMachineId && claimedMachineId === m.id) {
            li.classList.add('machine-highlight');
            if (typeof li.scrollIntoView === 'function') {
              setTimeout(() => li.scrollIntoView({ behavior: 'smooth', block: 'center' }), 100);
            }
            highlighted = true;
          }
        });
      }
      renderMachineOptions();
      renderQrCodes();
      if (highlighted) {
        if (help) help.style.display = 'block';
        claimedMachineId = null;
      } else if (help) {
        help.style.display = 'none';
      }
    } catch (error) {}
  }

  async function assignMachine(machineId, locationId) {
    const res = await OriginApi.assignMachine(machineId, locationId);
    if (res.ok) {
      showToast('Machine location updated', 'success');
      if (document.getElementById('machines-list')) loadMachines();
      if (currentLocationId === Number(locationId)) loadLocationMachines();
      const help = document.getElementById('machine-setup-message');
      if (help) help.style.display = 'none';
    } else {
      showToast('Failed to assign machine', 'error');
    }
  }

  async function unregisterMachine(machineId) {
    const res = await OriginApi.removeMachine(machineId);
    if (res.ok) {
      showToast('Machine unregistered', 'success');
      loadMachines();
      loadLocations();
      const help = document.getElementById('machine-setup-message');
      if (help) help.style.display = 'none';
    } else {
      showToast('Failed to unregister machine', 'error');
    }
  }

  async function loadQrCodes() {
    try {
      const res = await OriginApi.getQrCodes();
      if (!res.ok) return;
      cachedQrCodes = await res.json();
      renderQrCodes();
    } catch (error) {}
  }

  async function updateQrAssignment(qrId, machineId) {
    try {
      const res = await OriginApi.assignQrCode(qrId, machineId);
      if (!res.ok) {
        showToast('Failed to update QR code', 'error');
        return false;
      }
      const updated = await res.json();
      const index = cachedQrCodes.findIndex(qr => qr.id === updated.id);
      if (index >= 0) {
        cachedQrCodes[index] = updated;
      } else {
        cachedQrCodes.push(updated);
      }
      renderQrCodes();
      showToast('QR code updated', 'success');
      if (document.getElementById('machines-list')) loadMachines();
      return true;
    } catch (error) {
      showToast('Failed to update QR code', 'error');
      return false;
    }
  }

  function renderQrCodes() {
    const list = document.getElementById('qr-codes-list');
    const empty = document.getElementById('qr-codes-empty');
    if (!list || !empty) return;

    if (typeof list.replaceChildren === 'function') {
      list.replaceChildren();
    } else {
      list.innerHTML = '';
      if (Array.isArray(list.children)) list.children.length = 0;
    }

    if (!cachedQrCodes.length) {
      empty.style.display = 'block';
      return;
    }

    empty.style.display = 'none';

    cachedQrCodes.forEach(qr => {
      const item = document.createElement('li');
      item.className = 'qr-code-item';

      const header = document.createElement('div');
      header.className = 'qr-code-header';

      const info = createQrInfo(qr);
      info.classList.add('qr-code-info');
      header.appendChild(info);

      const actions = createQrActions(qr);
      actions.classList.add('qr-code-actions');
      header.appendChild(actions);

      item.appendChild(header);

      const assignment = document.createElement('div');
      assignment.className = 'qr-code-assignment';

      const select = document.createElement('select');
      select.className = 'qr-code-select';
      select.dataset.qr = qr.id;

      const hasMachines = Array.isArray(cachedMachines) && cachedMachines.length > 0;
      const defaultOpt = document.createElement('option');
      defaultOpt.value = '';
      defaultOpt.textContent = hasMachines ? 'Unassigned' : 'No machines available';
      select.appendChild(defaultOpt);

      if (!hasMachines) {
        select.disabled = true;
      } else {
        const sortedMachines = [...cachedMachines].sort((a, b) => {
          return getMachineLabel(a).localeCompare(getMachineLabel(b));
        });
        sortedMachines.forEach(machine => {
          const option = document.createElement('option');
          option.value = machine.id;
          option.textContent = getMachineLabel(machine);
          if (String(qr.machine_id || '') === String(machine.id)) option.selected = true;
          select.appendChild(option);
        });
      }

      const status = document.createElement('span');
      status.className = 'qr-code-status';
      if (qr.machine_label) {
        status.textContent = `Assigned to ${qr.machine_label}`;
      } else if (hasMachines) {
        status.textContent = 'Not assigned';
      } else {
        status.textContent = 'Claim a machine to assign this code';
      }

      select.onchange = async () => {
        select.disabled = true;
        const success = await updateQrAssignment(qr.id, select.value || null);
        if (!success) {
          select.disabled = false;
          renderQrCodes();
        }
      };

      assignment.appendChild(select);
      assignment.appendChild(status);
      item.appendChild(assignment);

      list.appendChild(item);
    });
  }

  function openLocation(loc = null) {
    currentLocationId = loc ? loc.id : null;
    currentLocation = loc;
    const title = document.getElementById('location-detail-title');
    const form = document.getElementById('location-detail-form');
    const view = document.getElementById('location-view');
    const editBtn = document.getElementById('edit-location-btn');
    const deleteBtn = document.getElementById('delete-location-btn');
    if (title) title.textContent = loc ? loc.name : 'Add Location';
    if (loc) {
      if (view) {
        document.getElementById('view-address').textContent = loc.address || '';
        const website = document.getElementById('view-website');
        if (website) {
          if (loc.website) {
            try {
              const url = new URL(loc.website);
              if (url.protocol === 'http:' || url.protocol === 'https:') {
                website.textContent = loc.website;
                website.href = loc.website;
                website.target = '_blank';
              } else {
                website.textContent = '';
                website.removeAttribute('href');
                website.removeAttribute('target');
              }
            } catch (error) {
              website.textContent = '';
              website.removeAttribute('href');
              website.removeAttribute('target');
            }
          } else {
            website.textContent = '';
            website.removeAttribute('href');
            website.removeAttribute('target');
          }
        }
        document.getElementById('view-hours').textContent = loc.hours || '';
        view.style.display = 'block';
      }
      updateLocationDashboard(loc);
      if (form) form.style.display = 'none';
      const isOwner = cachedLocations.some(l => l.id === loc.id);
      if (editBtn) editBtn.style.display = isOwner ? 'block' : 'none';
      if (deleteBtn) deleteBtn.style.display = 'none';
      if (currentLocationId) loadLocationMachines(false);
    } else {
      if (view) view.style.display = 'none';
      updateLocationDashboard(null);
      if (form) {
        form.reset();
        form.style.display = 'block';
        document.getElementById('detail-name').value = '';
        document.getElementById('detail-address').value = '';
        document.getElementById('detail-website').value = '';
        document.getElementById('detail-hours').value = '';
      }
      if (editBtn) editBtn.style.display = 'none';
      if (deleteBtn) deleteBtn.style.display = 'none';
      const ml = document.getElementById('location-machines-list');
      if (ml) ml.innerHTML = '';
    }
    showPage('location-detail');
  }

  function enableLocationEdit() {
    const form = document.getElementById('location-detail-form');
    const view = document.getElementById('location-view');
    const editBtn = document.getElementById('edit-location-btn');
    const deleteBtn = document.getElementById('delete-location-btn');
    if (editBtn) editBtn.style.display = 'none';
    if (view) view.style.display = 'none';
    if (form) {
      form.reset();
      document.getElementById('detail-name').value = currentLocation ? currentLocation.name : '';
      document.getElementById('detail-address').value = currentLocation ? currentLocation.address || '' : '';
      document.getElementById('detail-website').value = currentLocation ? currentLocation.website || '' : '';
      document.getElementById('detail-hours').value = currentLocation ? currentLocation.hours || '' : '';
      form.style.display = 'block';
    }
    if (deleteBtn) deleteBtn.style.display = currentLocationId ? 'inline-flex' : 'none';
    if (currentLocationId) loadLocationMachines(true);
  }

  async function saveLocation(e) {
    e.preventDefault();
    const data = {
      name: document.getElementById('detail-name').value,
      address: document.getElementById('detail-address').value,
      website: document.getElementById('detail-website').value,
      hours: document.getElementById('detail-hours').value
    };
    let res;
    if (currentLocationId) {
      res = await OriginApi.updateLocation(currentLocationId, data);
    } else {
      res = await OriginApi.createLocation(data);
    }
    if (res.ok) {
      const loc = await res.json();
      currentLocationId = loc.id;
      loadLocations();
      showPage('settings');
    } else {
      showToast('Failed to save location', 'error');
    }
  }

  async function handleLocationDelete() {
    if (!currentLocationId) return;
    const deleteTarget =
      currentLocation || cachedLocations.find(loc => loc.id === currentLocationId) || null;
    const name = deleteTarget && deleteTarget.name ? deleteTarget.name : 'this location';
    const message =
      `Delete ${name}? Machines assigned here will move to Unassigned and their scores will be kept.`;
    const confirmed = typeof global.confirm === 'function' ? global.confirm(message) : true;
    if (!confirmed) return;

    const res = await OriginApi.deleteLocation(currentLocationId);
    if (!res.ok) {
      showToast('Failed to delete location', 'error');
      return;
    }

    showToast('Location deleted', 'success');
    cachedLocations = cachedLocations.filter(loc => loc.id !== currentLocationId);
    currentLocationId = null;
    currentLocation = null;

    const form = document.getElementById('location-detail-form');
    if (form) {
      form.reset();
      form.style.display = 'none';
    }
    const view = document.getElementById('location-view');
    if (view) view.style.display = 'none';
    const editBtn = document.getElementById('edit-location-btn');
    if (editBtn) editBtn.style.display = 'none';
    const deleteBtn = document.getElementById('delete-location-btn');
    if (deleteBtn) deleteBtn.style.display = 'none';
    const machinesList = document.getElementById('location-machines-list');
    if (machinesList) machinesList.innerHTML = '';
    updateLocationDashboard(null);

    showPage('settings');
    loadLocations();
    loadMachines();
  }

  async function loadLocationMachines(editable = false) {
    if (!currentLocationId) return;
    try {
      const res = await OriginApi.getMachines();
      if (!res.ok) return;
      const machines = await res.json();
      const list = document.getElementById('location-machines-list');
      if (list) {
        list.innerHTML = '';
        machines.forEach(m => {
          if (editable) {
            const li = document.createElement('li');
            const label = getMachineLabel(m);
            li.textContent = label + ' ';
            const cb = document.createElement('input');
            cb.type = 'checkbox';
            cb.checked = m.location_id === currentLocationId;
            cb.onchange = () => {
              if (cb.checked) assignMachine(m.id, currentLocationId);
            };
            li.appendChild(cb);
            list.appendChild(li);
          } else if (m.location_id === currentLocationId) {
            const li = document.createElement('li');
            li.textContent = getMachineLabel(m);
            list.appendChild(li);
          }
        });
      }
    } catch (error) {}
  }

  function initSettings() {
    if (typeof location !== 'undefined') {
      try {
        const params = new URLSearchParams(location.search || '');
        const claimed = params.get('claimed_machine');
        if (claimed) {
          claimedMachineId = claimed;
          showToast('Machine claimed! Choose a location below to finish setup.', 'success');
          const help = document.getElementById('machine-setup-message');
          if (help) help.style.display = 'block';
          params.delete('claimed_machine');
          if (typeof history !== 'undefined' && history.replaceState) {
            const newQuery = params.toString();
            const newUrl = location.pathname + (newQuery ? `?${newQuery}` : '') + location.hash;
            history.replaceState(null, '', newUrl);
          }
        }
      } catch (error) {}
    }
    const addBtn = document.getElementById('add-location-btn');
    if (addBtn) addBtn.addEventListener('click', () => openLocation());
    const form = document.getElementById('location-detail-form');
    if (form) form.addEventListener('submit', saveLocation);
    const editBtn = document.getElementById('edit-location-btn');
    if (editBtn) editBtn.addEventListener('click', enableLocationEdit);
    const deleteBtn = document.getElementById('delete-location-btn');
    if (deleteBtn) deleteBtn.onclick = handleLocationDelete;
    loadLocations();
    loadMachines();
    loadQrCodes();
  }

  global.openLocation = openLocation;
  global.enableLocationEdit = enableLocationEdit;
  global.loadLocations = loadLocations;
  global.loadMachines = loadMachines;
  global.loadQrCodes = loadQrCodes;
  global.handleLocationDelete = handleLocationDelete;
  global.__setCachedLocations = locs => { cachedLocations = locs; };
  global.__setClaimedMachine = id => { claimedMachineId = id; };

  document.addEventListener('DOMContentLoaded', initSettings);
})(typeof window !== 'undefined' ? window : this);
