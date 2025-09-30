(function (global) {
  let cachedLocations = [];
  let currentLocationId = null;
  let currentLocation = null;
  let claimedMachineId = null;

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
    } catch {}
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
      if (highlighted) {
        if (help) help.style.display = 'block';
        claimedMachineId = null;
      } else if (help) {
        help.style.display = 'none';
      }
    } catch {}
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

  function openLocation(loc = null) {
    currentLocationId = loc ? loc.id : null;
    currentLocation = loc;
    const title = document.getElementById('location-detail-title');
    const form = document.getElementById('location-detail-form');
    const view = document.getElementById('location-view');
    const editBtn = document.getElementById('edit-location-btn');
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
            } catch {
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
      if (form) form.style.display = 'none';
      const isOwner = cachedLocations.some(l => l.id === loc.id);
      if (editBtn) editBtn.style.display = isOwner ? 'block' : 'none';
      if (currentLocationId) loadLocationMachines(false);
    } else {
      if (view) view.style.display = 'none';
      if (form) {
        form.reset();
        form.style.display = 'block';
        document.getElementById('detail-name').value = '';
        document.getElementById('detail-address').value = '';
        document.getElementById('detail-website').value = '';
        document.getElementById('detail-hours').value = '';
      }
      if (editBtn) editBtn.style.display = 'none';
      const ml = document.getElementById('location-machines-list');
      if (ml) ml.innerHTML = '';
    }
    showPage('location-detail');
  }

  function enableLocationEdit() {
    const form = document.getElementById('location-detail-form');
    const view = document.getElementById('location-view');
    const editBtn = document.getElementById('edit-location-btn');
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
    } catch {}
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
      } catch {}
    }
    const addBtn = document.getElementById('add-location-btn');
    if (addBtn) addBtn.addEventListener('click', () => openLocation());
    const form = document.getElementById('location-detail-form');
    if (form) form.addEventListener('submit', saveLocation);
    const editBtn = document.getElementById('edit-location-btn');
    if (editBtn) editBtn.addEventListener('click', enableLocationEdit);
    loadLocations();
    loadMachines();
  }

  global.openLocation = openLocation;
  global.enableLocationEdit = enableLocationEdit;
  global.loadLocations = loadLocations;
  global.loadMachines = loadMachines;
  global.__setCachedLocations = locs => { cachedLocations = locs; };
  global.__setClaimedMachine = id => { claimedMachineId = id; };

  document.addEventListener('DOMContentLoaded', initSettings);
})(typeof window !== 'undefined' ? window : this);
