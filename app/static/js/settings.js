(function (global) {
  let cachedLocations = [];

  async function loadLocations() {
    try {
      const res = await OriginApi.getLocations();
      if (!res.ok) return;
      cachedLocations = await res.json();
      const list = document.getElementById('locations-list');
      if (list) {
        list.innerHTML = '';
        cachedLocations.forEach(loc => {
          const li = document.createElement('li');
          li.textContent = loc.name;
          list.appendChild(li);
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

  async function createLocation(e) {
    e.preventDefault();
    const data = {
      name: document.getElementById('loc-name').value,
      address: document.getElementById('loc-address').value,
      website: document.getElementById('loc-website').value,
      hours: document.getElementById('loc-hours').value
    };
    const res = await OriginApi.createLocation(data);
    if (res.ok) {
      document.getElementById('location-form').reset();
      document.getElementById('location-form').style.display = 'none';
      loadLocations();
    } else {
      showToast('Failed to create location', 'error');
    }
  }

  async function assignMachine(machineId, locationId) {
    const res = await OriginApi.assignMachine(machineId, locationId);
    if (res.ok) {
      loadMachines();
    } else {
      showToast('Failed to assign machine', 'error');
    }
  }

  function initSettings() {
    const addBtn = document.getElementById('add-location-btn');
    if (addBtn) {
      addBtn.addEventListener('click', () => {
        const form = document.getElementById('location-form');
        if (form) form.style.display = 'block';
      });
    }
    const form = document.getElementById('location-form');
    if (form) form.addEventListener('submit', createLocation);
    loadLocations();
    loadMachines();
  }

  document.addEventListener('DOMContentLoaded', initSettings);
})(typeof window !== 'undefined' ? window : this);
