(function (global) {
  let cachedLocations = [];
  let currentLocationId = null;

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
        if (Number(sel.dataset.selected) === loc.id) opt.selected = true;
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
      if (list) {
        list.innerHTML = '';
        machines.forEach(m => {
          const li = document.createElement('li');
          li.textContent = m.name + ' ';
          const sel = document.createElement('select');
          sel.className = 'machine-location';
          sel.dataset.machine = m.id;
          sel.dataset.selected = m.location_id || '';
          li.appendChild(sel);
          list.appendChild(li);
        });
      }
      renderMachineOptions();
    } catch {}
  }

  async function assignMachine(machineId, locationId) {
    const res = await OriginApi.assignMachine(machineId, locationId);
    if (res.ok) {
      if (document.getElementById('machines-list')) loadMachines();
      if (currentLocationId === Number(locationId)) loadLocationMachines();
    } else {
      showToast('Failed to assign machine', 'error');
    }
  }

  function openLocation(loc = null) {
    currentLocationId = loc ? loc.id : null;
    const title = document.getElementById('location-detail-title');
    if (title) title.textContent = loc ? 'Edit Location' : 'Add Location';
    const form = document.getElementById('location-detail-form');
    if (form) {
      form.reset();
      document.getElementById('detail-name').value = loc ? loc.name : '';
      document.getElementById('detail-address').value = loc ? loc.address || '' : '';
      document.getElementById('detail-website').value = loc ? loc.website || '' : '';
      document.getElementById('detail-hours').value = loc ? loc.hours || '' : '';
    }
    showPage('location-detail');
    if (currentLocationId) loadLocationMachines();
    else {
      const ml = document.getElementById('location-machines-list');
      if (ml) ml.innerHTML = '';
    }
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

  async function loadLocationMachines() {
    if (!currentLocationId) return;
    try {
      const res = await OriginApi.getMachines();
      if (!res.ok) return;
      const machines = await res.json();
      const list = document.getElementById('location-machines-list');
      if (list) {
        list.innerHTML = '';
        machines.forEach(m => {
          const li = document.createElement('li');
          li.textContent = m.name + ' ';
          const cb = document.createElement('input');
          cb.type = 'checkbox';
          cb.checked = m.location_id === currentLocationId;
          cb.onchange = () => {
            if (cb.checked) assignMachine(m.id, currentLocationId);
          };
          li.appendChild(cb);
          list.appendChild(li);
        });
      }
    } catch {}
  }

  function initSettings() {
    const addBtn = document.getElementById('add-location-btn');
    if (addBtn) addBtn.addEventListener('click', () => openLocation());
    const form = document.getElementById('location-detail-form');
    if (form) form.addEventListener('submit', saveLocation);
    loadLocations();
    loadMachines();
  }

  document.addEventListener('DOMContentLoaded', initSettings);
})(typeof window !== 'undefined' ? window : this);
