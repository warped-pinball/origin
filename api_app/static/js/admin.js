const statusBanner = document.getElementById("status-banner");
const gameRoster = document.getElementById("game-roster");
const gamesStatus = document.getElementById("games-status");
const adminShell = document.getElementById("admin");
const logoutButton = document.getElementById("admin-logout");
const tournamentRoster = document.getElementById("tournament-roster");

const loginForm = document.getElementById("admin-login");
const loginModal = document.getElementById("login-modal");

if (loginModal && !loginModal.hidden) {
    document.body.classList.add("modal-open");
}

const tabButtons = document.querySelectorAll("[data-tab-target]");
const tabPanels = document.querySelectorAll(".tab-panel");

const GAME_REFRESH_MS = 10000;
const MACHINE_OFFLINE_MINUTES = 10;
const AUTH_STORAGE_KEY = "adminAuthHeader";

let authHeader = "";
let authenticated = false;
let gameRefreshTimer = null;
let cachedPlayers = [];
let cachedMachines = [];
let cachedTournaments = [];
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

const clearList = (node) => {
    while (node.firstChild) {
        node.removeChild(node.firstChild);
    }
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

const setActiveTab = (targetId) => {
    tabButtons.forEach((button) => {
        const isActive = button.dataset.tabTarget === targetId;
        button.classList.toggle("tab--current", isActive);
        button.setAttribute("aria-selected", isActive ? "true" : "false");
    });

    tabPanels.forEach((panel) => {
        panel.hidden = panel.id !== targetId;
    });
};

const openModal = (modal) => {
    modal.hidden = false;
    document.body.classList.add("modal-open");
};

const closeModal = (modal) => {
    modal.hidden = true;
    document.body.classList.remove("modal-open");
};

const unlockAdmin = () => {
    authenticated = true;
    adminShell.hidden = false;
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
    authenticated = false;
    localStorage.removeItem(AUTH_STORAGE_KEY);
    logoutButton.hidden = true;
    if (gameRefreshTimer) {
        clearInterval(gameRefreshTimer);
        gameRefreshTimer = null;
    }
};

const resetAdminUi = () => {
    clearList(gameRoster);
    const gamesHint = document.createElement("p");
    gamesHint.className = "hint";
    gamesHint.textContent = "No games detected yet.";
    gameRoster.appendChild(gamesHint);

    clearList(tournamentRoster);
    const tournamentHint = document.createElement("p");
    tournamentHint.className = "hint";
    tournamentHint.textContent = "No tournaments yet.";
    tournamentRoster.appendChild(tournamentHint);

    gamesStatus.textContent = "Listening for nearby boards…";
    adminShell.hidden = true;
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
    if (hours < 24) return `${hours} hour${hours === 1 ? "" : "s"} ago`;
    const days = Math.round(hours / 24);
    return `${days} day${days === 1 ? "" : "s"} ago`;
};

const formatDateRange = (start, end) => {
    const startDate = start ? new Date(start) : null;
    const endDate = end ? new Date(end) : null;
    if (!startDate && !endDate) return "No schedule";
    const options = { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" };
    if (startDate && endDate) {
        return `${startDate.toLocaleString([], options)} → ${endDate.toLocaleString([], options)}`;
    }
    if (startDate) return `Starts ${startDate.toLocaleString([], options)}`;
    return `Ends ${endDate.toLocaleString([], options)}`;
};

const getTournamentStatus = (tournament) => {
    const now = Date.now();
    const startMs = tournament.start_time ? Date.parse(tournament.start_time) : null;
    const endMs = tournament.end_time ? Date.parse(tournament.end_time) : null;
    const startValid = Number.isFinite(startMs);
    const endValid = Number.isFinite(endMs);

    const hasEnded = endValid && endMs < now;
    if (hasEnded) return "completed";

    if (!tournament.is_active) {
        if (!startValid || startMs <= now) {
            return "completed";
        }
        return "upcoming";
    }

    if (startValid && startMs > now) return "upcoming";
    return "active";
};

const createTournamentCard = (tournament) => {
    const status = getTournamentStatus(tournament);
    const card = document.createElement("div");
    card.className = "list__item list__item--interactive list__item--tournament";

    const header = document.createElement("div");
    header.className = "list__item__header";

    const badge = document.createElement("div");
    badge.className = "badge";
    badge.textContent = `${status.charAt(0).toUpperCase()}${status.slice(1)}`;

    const nameBlock = document.createElement("div");
    nameBlock.className = "list__item__title";
    const name = document.createElement("strong");
    name.textContent = tournament.name;
    const subtitle = document.createElement("p");
    subtitle.className = "hint";
    subtitle.textContent = formatDateRange(tournament.start_time, tournament.end_time);
    nameBlock.appendChild(name);
    nameBlock.appendChild(subtitle);

    header.appendChild(badge);
    header.appendChild(nameBlock);

    const detail = document.createElement("div");
    detail.className = "player-detail";
    detail.hidden = true;

    const summary = document.createElement("p");
    summary.className = "hint";
    const machineCount = tournament.machines?.length || 0;
    const playerCount = tournament.players?.length || 0;
    summary.textContent = `${machineCount} machine${machineCount === 1 ? "" : "s"} · ${playerCount || "all"} player${playerCount === 1 ? "" : "s"}`;

    const description = document.createElement("p");
    description.textContent = tournament.description || "No description provided.";

    const meta = document.createElement("p");
    meta.className = "hint";
    meta.textContent = `Display until: ${tournament.display_until ? new Date(tournament.display_until).toLocaleString() : "not set"}`;

    const type = document.createElement("p");
    type.className = "hint";
    type.textContent = `Type: ${tournament.tournament_type || tournament.scoring_profile?.name || "Custom"}`;

    const actions = document.createElement("div");
    actions.className = "actions actions--inline";

    const editButton = document.createElement("a");
    editButton.className = "button button--ghost";
    editButton.href = `/admin/tournaments/${encodeURIComponent(tournament.id)}`;
    editButton.textContent = "Edit";

    const deleteButton = document.createElement("button");
    deleteButton.type = "button";
    deleteButton.className = "button button--danger";
    deleteButton.textContent = "Delete";
    deleteButton.addEventListener("click", async (event) => {
        event.stopPropagation();
        await deleteTournament(tournament.id);
    });

    actions.append(editButton, deleteButton);

    detail.append(summary, description, type, meta, actions);

    header.addEventListener("click", () => {
        detail.hidden = !detail.hidden;
    });

    card.append(header, detail);
    return card;
};

const renderTournamentSection = (title, tournaments, { collapsed = false } = {}) => {
    const section = document.createElement("details");
    section.className = "tournament-section";
    section.open = !collapsed;

    const summary = document.createElement("summary");
    summary.className = "tournament-section__summary";
    summary.textContent = `${title} (${tournaments.length})`;
    section.appendChild(summary);

    const list = document.createElement("div");
    list.className = "tournament-section__list list list--cards";

    if (!tournaments.length) {
        const empty = document.createElement("p");
        empty.className = "hint";
        empty.textContent = `No ${title.toLowerCase()} tournaments.`;
        list.appendChild(empty);
    } else {
        tournaments.forEach((tournament) => {
            const card = createTournamentCard(tournament);
            list.appendChild(card);
        });
    }

    section.appendChild(list);
    tournamentRoster.appendChild(section);
};

const renderTournaments = (tournaments = []) => {
    clearList(tournamentRoster);
    cachedTournaments = tournaments;

    if (!tournaments.length) {
        const empty = document.createElement("p");
        empty.className = "hint";
        empty.textContent = "No tournaments yet.";
        tournamentRoster.appendChild(empty);
        return;
    }

    const buckets = { active: [], upcoming: [], completed: [] };
    tournaments.forEach((tournament) => {
        const bucket = getTournamentStatus(tournament);
        buckets[bucket].push(tournament);
    });

    const toMs = (value) => {
        const parsed = value ? Date.parse(value) : null;
        return Number.isFinite(parsed) ? parsed : null;
    };

    const sortByStart = (a, b) => (toMs(a.start_time) || Infinity) - (toMs(b.start_time) || Infinity);
    const sortByEndDesc = (a, b) => (toMs(b.end_time) || 0) - (toMs(a.end_time) || 0);

    buckets.active.sort(sortByStart);
    buckets.upcoming.sort(sortByStart);
    buckets.completed.sort(sortByEndDesc);

    renderTournamentSection("Active", buckets.active, { collapsed: false });
    renderTournamentSection("Upcoming", buckets.upcoming, { collapsed: false });
    renderTournamentSection("Completed", buckets.completed, { collapsed: true });
};

const getMachineBaseUrl = (ip) => {
    if (!ip) return null;
    return ip.startsWith("http") ? ip : `http://${ip}`;
};

const isMachineOnline = (timestamp) => {
    if (!timestamp) return false;
    const seen = new Date(timestamp).getTime();
    if (Number.isNaN(seen)) return false;
    const diff = Date.now() - seen;
    const clampedDiff = Math.max(0, diff);
    return clampedDiff <= MACHINE_OFFLINE_MINUTES * 60000;
};

const renderMachines = (games) => {
    clearList(gameRoster);
    cachedMachines = games;

    if (!games.length) {
        const empty = document.createElement("p");
        empty.className = "hint";
        empty.textContent = "No machines detected yet.";
        gameRoster.appendChild(empty);
        return;
    }

    const sorted = [...games].sort((a, b) => {
        const onlineDelta = Number(isMachineOnline(b.machine_last_seen)) - Number(isMachineOnline(a.machine_last_seen));
        if (onlineDelta !== 0) return onlineDelta;
        return (a.machine_name || "").localeCompare(b.machine_name || "");
    });

    sorted.forEach((game) => {
        const online = isMachineOnline(game.machine_last_seen);

        const card = document.createElement("div");
        card.className = "list__item list__item--interactive list__item--machine";
        card.role = "listitem";
        if (!online) {
            card.classList.add("list__item--offline");
        }

        const header = document.createElement("div");
        header.className = "list__item__header";

        const nameBlock = document.createElement("div");
        nameBlock.className = "list__item__title";

        const name = document.createElement("strong");
        name.textContent = game.machine_name || "Unknown machine";

        const meta = document.createElement("p");
        meta.className = "hint";
        const lastSeen = formatRelative(game.machine_last_seen);
        meta.textContent = lastSeen === "Unknown" ? "Last seen recently" : `Last seen ${lastSeen}`;

        nameBlock.appendChild(name);
        nameBlock.appendChild(meta);

        const statusPill = document.createElement("span");
        statusPill.className = `pill ${online ? "pill--success" : "pill--muted"}`;
        statusPill.textContent = online ? "Online" : "Offline";

        header.appendChild(nameBlock);

        const footer = document.createElement("div");
        footer.className = "list__item__footer";

        const passwordStatus = document.createElement("span");
        passwordStatus.className = `pill ${game.has_password ? "pill--success" : "pill--muted"}`;
        passwordStatus.textContent = game.has_password ? "Password set" : "No password";

        footer.appendChild(statusPill);
        footer.appendChild(passwordStatus);

        card.addEventListener("click", () => {
            const slug = game.machine_uid || game.id;
            if (slug) {
                window.location.href = `/admin/machines/${encodeURIComponent(slug)}`;
            }
        });

        card.appendChild(header);
        card.appendChild(footer);
        gameRoster.appendChild(card);
    });
};

const fetchPlayers = async (searchTerm = "") => {
    const params = new URLSearchParams();
    if (searchTerm) {
        params.set("search", searchTerm);
    }
    const url = `/api/v1/admin/players${params.size ? `?${params.toString()}` : ""}`;

    const response = await fetch(url, {
        headers: {
            Authorization: authHeader,
        },
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Unable to load players");
    }

    const payload = await response.json();
    if (!searchTerm) {
        cachedPlayers = payload;
    }
    return payload;
};

const updatePlayer = async (playerId, payload) => {
    const body = Object.entries(payload).reduce((acc, [key, value]) => {
        if (value !== null && value !== undefined && value !== "") {
            acc[key] = value;
        }
        return acc;
    }, {});

    const response = await fetch(`/api/v1/players/${playerId}`, {
        method: "PUT",
        headers: {
            "Content-Type": "application/json",
            Authorization: authHeader,
        },
        body: JSON.stringify(body),
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail?.message || error.detail || "Unable to save player");
    }

    return response.json();
};

const fetchTournaments = async () => {
    const response = await fetch("/api/v1/tournaments");
    if (!response.ok) {
        throw new Error("Unable to load tournaments");
    }
    const payload = await response.json();
    cachedTournaments = payload;
    return payload;
};

const deleteTournament = async (id) => {
    if (!authHeader) {
        setStatus("Sign in to manage tournaments.", "error");
        return;
    }

    setStatus("Deleting tournament…", "info");
    const response = await fetch(`/api/v1/tournaments/${id}`, {
        method: "DELETE",
        headers: {
            Authorization: authHeader,
        },
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        setStatus(error.detail || "Unable to delete tournament", "error");
        return;
    }

    await loadTournaments();
    setStatus("Tournament deleted.", "success");
};

const loadMachines = async () => {
    if (!authenticated) return;
    gamesStatus.textContent = "Scanning…";
    try {
        const response = await fetch("/api/v1/games/discovered");
        if (!response.ok) {
            throw new Error("Unable to load machines");
        }
        const games = await response.json();
        renderMachines(games);
        gamesStatus.textContent = games.length
            ? `Updated ${new Date().toLocaleTimeString()}`
            : "No machines detected yet.";
    } catch (error) {
        gamesStatus.textContent = error.message;
    }
};

const loadTournaments = async () => {
    try {
        const tournaments = await fetchTournaments();
        renderTournaments(tournaments);
    } catch (error) {
        setStatus(error.message, "error");
    }
};

const authenticateWithHeader = async (header) => {
    authHeader = header;
    setStatus("Signing in…", "info");

    try {
        await fetchPlayers();
        setStatus("Authenticated.", "success");
        unlockAdmin();
        persistAuth();
        await loadTournaments();
        loadMachines();
        if (!gameRefreshTimer) {
            gameRefreshTimer = setInterval(loadMachines, GAME_REFRESH_MS);
        }
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
        // already handled
    }
};

loginForm.addEventListener("submit", handleLogin);
logoutButton.addEventListener("click", () => {
    clearAuth();
    resetAdminUi();
    openModal(loginModal);
    setStatus("Signed out.", "info");
});

tabButtons.forEach((button) => {
    button.addEventListener("click", () => setActiveTab(button.dataset.tabTarget));
});

document.addEventListener("DOMContentLoaded", async () => {
    setActiveTab("games-panel");

    const storedHeader = localStorage.getItem(AUTH_STORAGE_KEY);
    if (storedHeader) {
        try {
            await authenticateWithHeader(storedHeader);
            return;
        } catch (error) {
            // fall through to login modal
        }
    }

    openModal(loginModal);
});
