const statusBanner = document.getElementById("status-banner");
const adminShell = document.getElementById("admin-tournament");
const tournamentForm = document.getElementById("tournament-form");
const tournamentSubmitButton = document.getElementById("tournament-submit");
const tournamentNameInput = document.getElementById("tournament-name");
const tournamentTypeSelect = document.getElementById("tournament-type");
const tournamentTypeDescription = document.getElementById("tournament-type-description");
const tournamentDescriptionInput = document.getElementById("tournament-description");
const tournamentStartInput = document.getElementById("tournament-start");
const tournamentEndInput = document.getElementById("tournament-end");
const tournamentDisplayUntilInput = document.getElementById("tournament-display-until");
const tournamentMachinesSelect = document.getElementById("tournament-machines");
const tournamentPlayersSelect = document.getElementById("tournament-players");
const tournamentMachineSearch = document.getElementById("tournament-machine-search");
const tournamentPlayerSearch = document.getElementById("tournament-player-search");
const formTitle = document.getElementById("form-title");
const formEyebrow = document.getElementById("form-eyebrow");
const formHint = document.getElementById("form-hint");

const loginForm = document.getElementById("admin-login");
const loginModal = document.getElementById("login-modal");

if (loginModal && !loginModal.hidden) {
    document.body.classList.add("modal-open");
}

const pathParts = window.location.pathname.split("/").filter(Boolean);
const lastPart = pathParts[pathParts.length - 1];
const editingTournamentId = lastPart === "new" ? null : Number(lastPart);
const isEditing = Number.isFinite(editingTournamentId);

const AUTH_STORAGE_KEY = "adminAuthHeader";

let authHeader = "";
let statusClearTimer = null;
let cachedTypes = [];
let machineOptions = [];
let playerOptions = [];
const selectedMachineIds = new Set();
const selectedPlayerIds = new Set();

const getToastStack = () => {
    let stack = document.querySelector(".toast-stack");
    if (!stack) {
        stack = document.createElement("div");
        stack.className = "toast-stack";
        stack.setAttribute("role", "status");
        stack.setAttribute("aria-live", "polite");
        document.body.appendChild(stack);
    }
    return stack;
};

const pushToast = (message, tone = "info") => {
    if (!message) return;
    const stack = getToastStack();
    const toast = document.createElement("div");
    toast.className = `toast toast--${tone}`;
    toast.textContent = message;
    stack.appendChild(toast);
    requestAnimationFrame(() => toast.classList.add("toast--visible"));
    setTimeout(() => {
        toast.classList.remove("toast--visible");
        setTimeout(() => toast.remove(), 240);
    }, 4200);
};

const setStatus = (message, tone = "info") => {
    if (statusBanner) {
        statusBanner.textContent = message;
        statusBanner.className = `status status--${tone}`;
        if (statusClearTimer) {
            clearTimeout(statusClearTimer);
        }
        if (message) {
            statusClearTimer = setTimeout(() => {
                statusBanner.textContent = "";
                statusBanner.className = "status";
            }, 3800);
        }
    }
    if (tone === "error") {
        pushToast(message, tone);
    }
};

const openModal = (modal) => {
    modal.hidden = false;
    document.body.classList.add("modal-open");
};

const closeModal = (modal) => {
    modal.hidden = true;
    document.body.classList.remove("modal-open");
};

const promptLogin = (message = "Sign in to manage tournaments.") => {
    if (message) {
        setStatus(message, "info");
    }
    openModal(loginModal);
};

const setDefaultTournamentTimes = () => {
    if (!tournamentStartInput || !tournamentEndInput || !tournamentDisplayUntilInput) return;

    const now = new Date();
    const end = new Date(now.getTime() + 2 * 60 * 60 * 1000);
    const displayUntil = new Date(end.getTime() + 60 * 60 * 1000);

    tournamentStartInput.value = now.toISOString().slice(0, 16);
    tournamentEndInput.value = end.toISOString().slice(0, 16);
    tournamentDisplayUntilInput.value = displayUntil.toISOString().slice(0, 16);
};

const populateSelect = (selectNode, items, { includeBlank = false } = {}) => {
    if (!selectNode) return;
    selectNode.innerHTML = "";
    if (includeBlank) {
        const option = document.createElement("option");
        option.value = "";
        option.textContent = "None";
        selectNode.appendChild(option);
    }
    items.forEach((item) => {
        const option = document.createElement("option");
        option.value = item.value;
        option.textContent = item.label;
        selectNode.appendChild(option);
    });
};

const filterChipItems = (items, query = "") => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) return items;
    return items.filter(({ label, meta }) =>
        [label, meta]
            .filter(Boolean)
            .some((text) => text.toLowerCase().includes(normalized)),
    );
};

const renderChipSelector = (container, items = [], selectionSet = new Set(), query = "") => {
    if (!container) return;
    container.innerHTML = "";

    const filteredItems = filterChipItems(items, query);

    if (!filteredItems.length) {
        const empty = document.createElement("p");
        empty.className = "hint";
        empty.textContent = query ? "No matches found." : "Nothing to select yet.";
        container.appendChild(empty);
        return;
    }

    const sortedItems = [...filteredItems].sort((a, b) => a.label.localeCompare(b.label));

    sortedItems.forEach((item) => {
        const numericValue = Number(item.value);
        const label = document.createElement("label");
        label.className = "chip-option";
        label.dataset.value = item.value;

        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.value = numericValue;
        checkbox.checked = selectionSet.has(numericValue);

        checkbox.addEventListener("change", () => {
            const numeric = Number(checkbox.value);
            if (checkbox.checked) {
                selectionSet.add(numeric);
            } else {
                selectionSet.delete(numeric);
            }
            label.classList.toggle("chip-option--active", checkbox.checked);
        });

        const title = document.createElement("span");
        title.className = "chip-option__title";
        title.textContent = item.label;

        label.appendChild(checkbox);
        label.appendChild(title);

        if (item.meta) {
            const meta = document.createElement("span");
            meta.className = "chip-option__meta";
            meta.textContent = item.meta;
            label.appendChild(meta);
        }

        label.classList.toggle("chip-option--active", checkbox.checked);
        container.appendChild(label);
    });
};

const setChipSelections = (selectionSet, ids = [], container, items, searchInput) => {
    selectionSet.clear();
    ids.forEach((id) => {
        const numeric = Number(id);
        if (!Number.isNaN(numeric)) {
            selectionSet.add(numeric);
        }
    });

    if (container && items) {
        renderChipSelector(container, items, selectionSet, searchInput?.value || "");
    }
};

const getSelectedIds = (selectionSet) => Array.from(selectionSet).filter((value) => !Number.isNaN(value));

const toIsoString = (value) => (value ? new Date(value).toISOString() : null);

const updateTypeDescription = () => {
    if (!tournamentTypeSelect || !tournamentTypeDescription) return;
    const selected = cachedTypes.find((type) => type.slug === tournamentTypeSelect.value);
    tournamentTypeDescription.textContent = selected?.description || "Choose a format to see its rules.";
};

const fetchTournamentTypes = async () => {
    const response = await fetch("/api/v1/tournaments/types");
    if (!response.ok) {
        throw new Error("Unable to load tournament types");
    }
    const payload = await response.json();
    cachedTypes = payload;
    populateSelect(
        tournamentTypeSelect,
        payload.map((type) => ({ value: type.slug, label: type.name })),
    );
    updateTypeDescription();
    return payload;
};

const fetchMachines = async () => {
    const response = await fetch("/api/v1/games/discovered");
    if (!response.ok) {
        throw new Error("Unable to load machines");
    }
    const games = await response.json();
    machineOptions = games.map((game) => ({
        value: game.machine_id || game.id,
        label: game.machine_name || "Unknown machine",
        meta: null,
    }));
    renderChipSelector(
        tournamentMachinesSelect,
        machineOptions,
        selectedMachineIds,
        tournamentMachineSearch?.value,
    );
    return games;
};

const fetchPlayers = async () => {
    const response = await fetch("/api/v1/admin/players", {
        headers: {
            Authorization: authHeader,
        },
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        const err = new Error(error.detail || "Unable to load players");
        err.status = response.status;
        throw err;
    }

    const payload = await response.json();
    playerOptions = payload.map((player) => ({
        value: player.id,
        label: player.screen_name || player.initials,
        meta: player.screen_name ? `${player.initials} · ${player.screen_name}` : player.initials,
    }));
    renderChipSelector(
        tournamentPlayersSelect,
        playerOptions,
        selectedPlayerIds,
        tournamentPlayerSearch?.value,
    );
    return payload;
};

const fetchTournamentDetail = async (id) => {
    const response = await fetch(`/api/v1/tournaments/${id}`);
    if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || "Unable to load tournament");
    }
    return response.json();
};

const populateTournamentForm = (tournament) => {
    tournamentSubmitButton.textContent = "Update tournament";
    formTitle.textContent = "Edit tournament";
    formEyebrow.textContent = `Tournament #${tournament.id}`;
    formHint.textContent = "Adjust the schedule, format, or roster.";

    tournamentNameInput.value = tournament.name;
    tournamentDescriptionInput.value = tournament.description || "";
    tournamentStartInput.value = tournament.start_time ? new Date(tournament.start_time).toISOString().slice(0, 16) : "";
    tournamentEndInput.value = tournament.end_time ? new Date(tournament.end_time).toISOString().slice(0, 16) : "";
    tournamentDisplayUntilInput.value = tournament.display_until
        ? new Date(tournament.display_until).toISOString().slice(0, 16)
        : "";

    const typeSlug =
        tournament.tournament_type ||
        cachedTypes.find(
            (type) =>
                type.scoring_profile_slug === tournament.scoring_profile?.slug &&
                type.game_mode_slug === tournament.game_mode?.slug,
        )?.slug;

    if (typeSlug) {
        tournamentTypeSelect.value = typeSlug;
        updateTypeDescription();
    }

    setChipSelections(
        selectedMachineIds,
        (tournament.machines || []).map((machine) => machine.machine_id || machine.id),
        tournamentMachinesSelect,
        machineOptions,
        tournamentMachineSearch,
    );
    setChipSelections(
        selectedPlayerIds,
        (tournament.players || []).map((player) => player.player_id || player.id),
        tournamentPlayersSelect,
        playerOptions,
        tournamentPlayerSearch,
    );
};

const unlockPage = () => {
    adminShell.hidden = false;
    closeModal(loginModal);
};

const persistAuth = () => {
    if (authHeader) {
        localStorage.setItem(AUTH_STORAGE_KEY, authHeader);
    }
};

const handleSubmit = async (event) => {
    event.preventDefault();
    if (!authHeader) {
        setStatus("Sign in to manage tournaments.", "error");
        return;
    }

    const payload = {
        name: tournamentNameInput.value.trim(),
        tournament_type: tournamentTypeSelect.value,
        description: tournamentDescriptionInput.value.trim() || null,
        start_time: toIsoString(tournamentStartInput.value),
        end_time: toIsoString(tournamentEndInput.value),
        display_until: toIsoString(tournamentDisplayUntilInput.value),
        machine_ids: getSelectedIds(selectedMachineIds),
        player_ids: getSelectedIds(selectedPlayerIds),
    };

    setStatus(isEditing ? "Updating tournament…" : "Creating tournament…", "info");
    try {
        const url = isEditing ? `/api/v1/tournaments/${editingTournamentId}` : "/api/v1/tournaments";
        const response = await fetch(url, {
            method: isEditing ? "PATCH" : "POST",
            headers: {
                "Content-Type": "application/json",
                Authorization: authHeader,
            },
            body: JSON.stringify(payload),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || "Unable to save tournament");
        }

        setStatus(isEditing ? "Tournament updated." : "Tournament created.", "success");
        window.location.href = "/admin#tournaments-panel";
    } catch (error) {
        setStatus(error.message, "error");
    }
};

const authenticateWithHeader = async (header) => {
    authHeader = header;
    setStatus("Signing in…", "info");

    try {
        await Promise.all([fetchTournamentTypes(), fetchMachines(), fetchPlayers()]);
        setDefaultTournamentTimes();
        if (isEditing) {
            const tournament = await fetchTournamentDetail(editingTournamentId);
            populateTournamentForm(tournament);
        }
        unlockPage();
        persistAuth();
        setStatus("Authenticated.", "success");
    } catch (error) {
        authHeader = "";
        if (error.status === 401 || error.status === 403) {
            setStatus("Session expired. Please sign in again.", "error");
            openModal(loginModal);
        } else {
            setStatus(error.message, "error");
        }
        throw error;
    }
};

const handleLogin = async (event) => {
    event.preventDefault();
    const password = event.target.password.value;
    const header = `Basic ${btoa(`admin:${password}`)}`;
    try {
        await authenticateWithHeader(header);
    } catch (error) {
        // already handled
    }
};

if (tournamentTypeSelect) {
    tournamentTypeSelect.addEventListener("change", updateTypeDescription);
}

if (tournamentForm) {
    tournamentForm.addEventListener("submit", handleSubmit);
}

if (tournamentMachineSearch) {
    tournamentMachineSearch.addEventListener("input", () =>
        renderChipSelector(
            tournamentMachinesSelect,
            machineOptions,
            selectedMachineIds,
            tournamentMachineSearch.value,
        ),
    );
}

if (tournamentPlayerSearch) {
    tournamentPlayerSearch.addEventListener("input", () =>
        renderChipSelector(
            tournamentPlayersSelect,
            playerOptions,
            selectedPlayerIds,
            tournamentPlayerSearch.value,
        ),
    );
}

loginForm.addEventListener("submit", handleLogin);

document.addEventListener("DOMContentLoaded", async () => {
    if (isEditing) {
        formTitle.textContent = "Edit tournament";
        formHint.textContent = "Adjust the schedule, format, or roster.";
        formEyebrow.textContent = "Tournament";
        tournamentSubmitButton.textContent = "Update tournament";
    }

    let authenticated = false;
    const storedHeader = localStorage.getItem(AUTH_STORAGE_KEY);
    if (storedHeader) {
        try {
            await authenticateWithHeader(storedHeader);
            authenticated = true;
        } catch (error) {
            // fall through to login modal
        }
    }

    if (!authenticated && loginModal?.hidden) {
        const hasStatus = Boolean(statusBanner?.textContent);
        promptLogin(hasStatus ? "" : undefined);
    }
});
