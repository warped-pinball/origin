const statusBanner = document.getElementById("status-banner");
const logoutButton = document.getElementById("admin-logout");
const machineShell = document.getElementById("machine-admin");
const loginForm = document.getElementById("admin-login");
const loginModal = document.getElementById("login-modal");
const machineTitle = document.getElementById("machine-title");
const machineSubtitle = document.getElementById("machine-subtitle");
const machineMeta = document.getElementById("machine-meta");
const machineLastSeen = document.getElementById("machine-last-seen");
const machineStatus = document.getElementById("machine-status");
const machineLastSeenDetail = document.getElementById("machine-last-seen-detail");
const machineNetwork = document.getElementById("machine-network");
const machinePasswordStatus = document.getElementById("machine-password-status");
const machineOpenLink = document.getElementById("machine-open-link");
const machineSetPasswordButton = document.getElementById("machine-set-password");
const machineAuthStatus = document.getElementById("machine-auth-status");
const machineCheckUpdatesButton = document.getElementById("machine-check-updates");
const machineApplyUpdateButton = document.getElementById("machine-apply-update");
const machineVersion = document.getElementById("machine-version");
const machineUpdateStatus = document.getElementById("machine-update-status");
const liveSection = document.getElementById("machine-live-section");
const liveMeta = document.getElementById("live-game-meta");
const liveScores = document.getElementById("live-game-scores");
const liveUpdated = document.getElementById("live-game-updated");
const gamePasswordModal = document.getElementById("game-password-modal");
const gamePasswordForm = document.getElementById("game-password-form");
const gamePasswordTitle = document.getElementById("game-password-title");
const gamePasswordHint = document.getElementById("game-password-hint");
const gamePasswordInput = document.getElementById("game-password-input");
const gameIdField = document.getElementById("game-id-field");
const closeGameModalButton = document.getElementById("close-game-modal");
const cancelGameModalButton = document.getElementById("cancel-game-modal");

const MACHINE_OFFLINE_MINUTES = 10;
const UPDATE_CHECK_MS = 5 * 60 * 1000;
const AUTH_STORAGE_KEY = "adminAuthHeader";

let authHeader = "";
let selectedMachine = null;
let selectedMachineUpdate = null;
let livePollTimer = null;
const updateCheckCache = new Map();
let statusClearTimer = null;

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

const unlockPage = () => {
    machineShell.hidden = false;
    logoutButton.hidden = false;
    closeModal(loginModal);
};

const persistAuth = () => {
    if (authHeader) {
        localStorage.setItem(AUTH_STORAGE_KEY, authHeader);
    }
};

const clearAuth = () => {
    authHeader = "";
    localStorage.removeItem(AUTH_STORAGE_KEY);
    logoutButton.hidden = true;
};

const formatRelative = (timestamp) => {
    if (!timestamp) return "Unknown";
    const date = new Date(timestamp);
    const diffMs = Date.now() - date.getTime();
    if (Number.isNaN(diffMs)) return "Unknown";

    const minutes = Math.max(0, Math.round(diffMs / 60000));
    if (minutes <= 1) return "just now";
    if (minutes < 60) return `${minutes} min ago`;
    const hours = Math.round(minutes / 60);
    return `${hours} hour${hours === 1 ? "" : "s"} ago`;
};

const getMachineBaseUrl = (ip) => {
    if (!ip) return null;
    return ip.startsWith("http") ? ip : `http://${ip}`;
};

const formatClock = (seconds) => {
    const total = Math.max(0, Number(seconds) || 0);
    const mins = Math.floor(total / 60);
    const secs = total % 60;
    return `${mins}:${secs.toString().padStart(2, "0")}`;
};

const isMachineOnline = (timestamp) => {
    if (!timestamp) return false;
    const seen = new Date(timestamp).getTime();
    if (Number.isNaN(seen)) return false;
    const diff = Date.now() - seen;
    const clamped = Math.max(0, diff);
    return clamped <= MACHINE_OFFLINE_MINUTES * 60000;
};

const getMachineSlug = () => {
    const match = window.location.pathname.match(/^\/admin\/machines\/([^/]+)/);
    return match ? decodeURIComponent(match[1]) : null;
};

const fetchMachineVersion = async (machineId) => {
    const response = await fetch(`/api/v1/admin/games/${machineId}/version`, {
        headers: { Authorization: authHeader },
    });
    if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        console.warn("Unable to refresh machine version", { status: response.status, error });
        throw new Error(error.detail || "Unable to refresh machine version.");
    }
    return response.json();
};

const fetchUpdateInfo = async (machine) => {
    if (!machine?.id) {
        throw new Error("Machine missing id.");
    }

    if (updateCheckCache.has(machine.id)) {
        const cached = updateCheckCache.get(machine.id);
        if (Date.now() - cached.timestamp < UPDATE_CHECK_MS) {
            return cached.data;
        }
    }

    const response = await fetch(`/api/v1/admin/games/${machine.id}/updates/check`, {
        headers: { Authorization: authHeader },
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || "Unable to check for updates.");
    }

    const data = await response.json();
    updateCheckCache.set(machine.id, { timestamp: Date.now(), data });
    return data;
};

const applyMachineUpdate = async (machine, url) => {
    if (!machine?.id) {
        throw new Error("Machine missing id.");
    }
    const response = await fetch(`/api/v1/admin/games/${machine.id}/updates/apply`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: authHeader },
        body: JSON.stringify({ url }),
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || "Unable to start update.");
    }

    return response.json();
};

const showUpdateInfo = (update) => {
    selectedMachineUpdate = null;
    machineApplyUpdateButton.disabled = true;
    machineUpdateStatus.textContent = "";

    if (!update) {
        machineUpdateStatus.textContent = "Check for updates to see what's new.";
        return;
    }

    const summary = document.createElement("span");
    summary.textContent = `Update available${update.version ? `: ${update.version}` : ""}.`;

    machineUpdateStatus.appendChild(summary);
    if (update.release_page) {
        machineUpdateStatus.appendChild(document.createElement("br"));
        const link = document.createElement("a");
        link.href = update.release_page;
        link.target = "_blank";
        link.rel = "noopener";
        link.textContent = "View release notes";
        machineUpdateStatus.appendChild(link);
    }

    selectedMachineUpdate = update;
    machineApplyUpdateButton.disabled = !update.url;
};

const renderLiveScores = (scores = []) => {
    liveScores.innerHTML = "";
    if (!scores.length) {
        const empty = document.createElement("div");
        empty.className = "live-panel__score";
        empty.textContent = "Waiting for scores…";
        liveScores.appendChild(empty);
        return;
    }

    scores.forEach((entry) => {
        const row = document.createElement("div");
        row.className = "live-panel__score";

        const label = document.createElement("span");
        label.className = "live-panel__score-label";
        label.textContent = `P${entry.player_number}`;

        const value = document.createElement("span");
        value.textContent = `${entry.screen_name || entry.initials || "Player"} — ${entry.score.toLocaleString()}`;

        row.append(label, value);
        liveScores.appendChild(row);
    });
};

const showLiveGame = (state) => {
    if (!state || !liveSection) return;
    liveSection.hidden = false;
    liveMeta.textContent = `Ball ${state.ball} · Player ${state.player_up} · ${formatClock(state.seconds_elapsed)}`;
    liveUpdated.textContent = `Last updated ${formatRelative(state.updated_at)}`;
    renderLiveScores(state.scores || []);
};

const hideLiveGame = (message = "No active game.", { visible = false } = {}) => {
    if (!liveSection) return;
    liveSection.hidden = !visible;
    liveMeta.textContent = message;
    liveUpdated.textContent = visible ? "Waiting for game data…" : "";
    liveScores.innerHTML = "";
};

const fetchLiveGameState = async (gameId) => {
    const response = await fetch(`/api/v1/games/${gameId}/live`);
    if (!response.ok) {
        throw new Error("Unable to load live game state.");
    }

    return response.json();
};

const startLivePolling = (machine) => {
    if (livePollTimer) {
        clearInterval(livePollTimer);
    }

    if (!machine?.is_active || !machine.id) {
        hideLiveGame();
        livePollTimer = null;
        return;
    }

    const loadState = async () => {
        try {
            const state = await fetchLiveGameState(machine.id);
            showLiveGame(state);
        } catch (error) {
            hideLiveGame(error.message, { visible: true });
        }
    };

    loadState();
    livePollTimer = setInterval(loadState, 2000);
};

const openGamePasswordModal = (game) => {
    gameIdField.value = game.id;
    gamePasswordTitle.textContent = `Set password for ${game.machine_name || "game"}`;
    gamePasswordHint.textContent = game.machine_ip
        ? `Requests to ${game.machine_ip} will use this password.`
        : "Requests for this game will use this password.";
    gamePasswordInput.value = "";
    openModal(gamePasswordModal);
    gamePasswordInput.focus();
};

const closeGamePasswordModal = () => {
    gamePasswordForm.reset();
    closeModal(gamePasswordModal);
};

const saveGamePassword = async (gameId, password) => {
    const response = await fetch(`/api/v1/admin/games/${gameId}/password`, {
        method: "PUT",
        headers: {
            "Content-Type": "application/json",
            Authorization: authHeader,
        },
        body: JSON.stringify({ password }),
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail?.message || error.detail || "Unable to save password");
    }

    return response.json();
};

const fetchMachines = async () => {
    const response = await fetch("/api/v1/games/discovered");
    if (!response.ok) {
        throw new Error("Unable to load machine details.");
    }
    return response.json();
};

const renderMachine = async (machine) => {
    selectedMachine = machine;

    const online = isMachineOnline(machine.machine_last_seen);
    const lastSeen = formatRelative(machine.machine_last_seen);
    const baseUrl = getMachineBaseUrl(machine.machine_ip);

    machineTitle.textContent = machine.machine_name || "Machine";
    machineSubtitle.textContent = online ? "Online" : "Offline";
    machineMeta.textContent = `${machine.machine_ip || "IP unknown"} • UID: ${
        machine.machine_uid || "UID unknown"
    }`;
    machineLastSeen.textContent = `Seen ${lastSeen}`;
    machineStatus.textContent = online ? "Online" : "Offline";
    machineLastSeenDetail.textContent = lastSeen;
    machineNetwork.textContent = machine.machine_ip || "IP unknown";

    machineOpenLink.href = baseUrl || "#";
    machineOpenLink.textContent = baseUrl ? "Open web UI" : "IP unavailable";
    machineOpenLink.setAttribute("aria-disabled", baseUrl ? "false" : "true");

    machinePasswordStatus.textContent = machine.has_password ? "Password set" : "No password set";
    machineSetPasswordButton.disabled = !machine.id;
    machineSetPasswordButton.onclick = () => openGamePasswordModal(machine);

    machineAuthStatus.textContent = machine.has_password
        ? "Password stored for authenticated requests."
        : "Use the password modal to store credentials for this machine.";

    startLivePolling(machine);
    
    const checkedAgo = formatRelative(machine.machine_version_checked_at);
    const versionText = machine.machine_version || "Unknown";
    machineVersion.textContent = `Version: ${versionText}${
        checkedAgo && checkedAgo !== "Unknown" ? ` (checked ${checkedAgo})` : ""
    }`;

    const cachedUpdate = updateCheckCache.get(machine.id);
    showUpdateInfo(cachedUpdate?.data || null);

    machineCheckUpdatesButton.onclick = async () => {
        if (!selectedMachine || selectedMachine.id !== machine.id) return;
        setStatus("Checking for updates…", "info");
        try {
            const update = await fetchUpdateInfo(machine);
            showUpdateInfo(update);
            setStatus("Update check complete.", "success");
        } catch (error) {
            machineUpdateStatus.textContent = error.message;
            setStatus(error.message, "error");
        }
    };

    machineApplyUpdateButton.onclick = async () => {
        if (!selectedMachine || selectedMachine.id !== machine.id || !selectedMachineUpdate?.url) return;
        setStatus("Starting update…", "info");
        try {
            await applyMachineUpdate(machine, selectedMachineUpdate.url);
            setStatus("Update started.", "success");
        } catch (error) {
            setStatus(error.message, "error");
        }
    };
};

const loadMachine = async () => {
    const slug = getMachineSlug();
    if (!slug) {
        setStatus("Missing machine id.", "error");
        return;
    }

    setStatus("Loading machine…", "info");
    try {
        const machines = await fetchMachines();
        const machine = machines.find(
            (entry) => entry.machine_uid === slug || String(entry.id) === slug
        );

        if (!machine) {
            setStatus("Machine not found.", "error");
            machineSubtitle.textContent = "Machine offline or unavailable.";
            return;
        }

        try {
            const versionStatus = await fetchMachineVersion(machine.id);
            machine.machine_version = versionStatus.machine_version;
            machine.machine_version_checked_at = versionStatus.machine_version_checked_at;
        } catch (error) {
            console.warn("Unable to refresh machine version", error);
        }

        await renderMachine(machine);
        setStatus("", "info");
    } catch (error) {
        setStatus(error.message, "error");
    }
};

const authenticateWithHeader = async (header) => {
    authHeader = header;
    setStatus("Signing in…", "info");

    try {
        await fetchMachines();
        setStatus("Authenticated.", "success");
        unlockPage();
        persistAuth();
        await loadMachine();
    } catch (error) {
        clearAuth();
        setStatus(error.message, "error");
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
        // handled in authenticate
    }
};

const handleGamePasswordSubmit = async (event) => {
    event.preventDefault();
    if (!authHeader) return;

    const password = gamePasswordInput.value.trim();
    const gameId = gameIdField.value;
    if (!password) return;

    setStatus("Saving game password…", "info");
    try {
        await saveGamePassword(gameId, password);
        setStatus("Game password saved.", "success");
        closeGamePasswordModal();
        await loadMachine();
    } catch (error) {
        setStatus(error.message, "error");
    }
};

loginForm.addEventListener("submit", handleLogin);
gamePasswordForm.addEventListener("submit", handleGamePasswordSubmit);
closeGameModalButton.addEventListener("click", closeGamePasswordModal);
cancelGameModalButton.addEventListener("click", closeGamePasswordModal);
logoutButton.addEventListener("click", () => {
    clearAuth();
    window.location.href = "/admin";
});

document.addEventListener("DOMContentLoaded", async () => {
    const storedHeader = localStorage.getItem(AUTH_STORAGE_KEY);
    if (storedHeader) {
        try {
            await authenticateWithHeader(storedHeader);
            return;
        } catch (error) {
            // fall back to login modal
        }
    }

    openModal(loginModal);
});
