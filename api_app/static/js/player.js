const form = document.getElementById("player-form");
const statusBanner = document.getElementById("status-banner");
const badgeInitials = document.getElementById("badge-initials");
const summaryName = document.getElementById("summary-name");
const summaryScreen = document.getElementById("summary-screen");
const summaryContact = document.getElementById("summary-contact");
const playerNameHeading = document.getElementById("player-name");
const pageTitle = document.getElementById("page-title");
const saveButton = document.getElementById("save-button");
const editPanel = document.getElementById("edit-panel");
const editButton = document.getElementById("edit-button");
const statsTotal = document.getElementById("stats-total");
const statsRecent = document.getElementById("stats-recent");
const statsBest = document.getElementById("stats-best");
let initialSnapshot = null;
let isEditing = false;
let statusClearTimer = null;

const playerId = (() => {
    const segments = window.location.pathname.split("/").filter(Boolean);
    const idSegment = segments[1];
    const id = Number.parseInt(idSegment, 10);
    return Number.isFinite(id) ? id : null;
})();

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

const formatErrorDetail = (detail) => {
    if (!detail) {
        return "Could not save player";
    }
    if (Array.isArray(detail)) {
        return detail.map((item) => item.msg).filter(Boolean).join("; ") || "Could not save player";
    }
    if (typeof detail === "string") {
        return detail;
    }
    const baseMessage = detail.message || "Could not save player";
    if (Array.isArray(detail.suggestions) && detail.suggestions.length) {
        return `${baseMessage} Try ${detail.suggestions.join(", ")}.`;
    }
    return baseMessage;
};

const serializeForm = (formNode) => {
    const data = new FormData(formNode);
    const payload = {};
    data.forEach((value, key) => {
        if (value !== null && value !== "") {
            payload[key] = value;
        }
    });
    return payload;
};

const renderSummary = (player) => {
    badgeInitials.textContent = player.initials || "---";
    const fullName = [player.first_name, player.last_name].filter(Boolean).join(" ");
    summaryName.textContent = fullName || player.screen_name || "No name provided";
    summaryScreen.textContent = player.screen_name ? `Screen: ${player.screen_name}` : "";
    summaryContact.textContent = "Contact info stays private.";
};

const renderStats = (stats = {}) => {
    const totalGames = stats.total_games ?? 0;
    statsTotal.textContent = `Total games: ${totalGames}`;

    if (stats.last_game) {
        const machine = stats.last_game.machine_name || "Unknown machine";
        const time = stats.last_game.start_time ? new Date(stats.last_game.start_time).toLocaleString() : "Unknown time";
        const score = stats.last_game.score != null ? ` • Score: ${stats.last_game.score.toLocaleString()}` : "";
        statsRecent.textContent = `Most recent: ${machine} (${time})${score}`;
    } else {
        statsRecent.textContent = "Most recent: No games yet.";
    }

    if (stats.best_score != null) {
        statsBest.textContent = `Best score: ${stats.best_score.toLocaleString()}`;
    } else {
        statsBest.textContent = "Best score: Not recorded yet.";
    }
};

const getFormSnapshot = () => ({
    initials: form.initials.value || "",
    screen_name: form.screen_name.value || "",
    first_name: form.first_name.value || "",
    last_name: form.last_name.value || "",
    email: form.email.value || "",
    phone_number: form.phone_number.value || "",
});

const hasChanges = () => {
    if (!initialSnapshot) return false;
    const current = getFormSnapshot();
    return Object.keys(initialSnapshot).some((key) => initialSnapshot[key] !== current[key]);
};

const hasContact = () => Boolean(form.email.value.trim() || form.phone_number.value.trim());

const updateSaveButtonState = () => {
    const canSave = hasChanges() && hasContact();
    saveButton.hidden = !canSave;
};

const recordInitialSnapshot = () => {
    initialSnapshot = getFormSnapshot();
    updateSaveButtonState();
};

const populateForm = (player) => {
    form.initials.value = player.initials || "";
    form.screen_name.value = player.screen_name || "";
    form.first_name.value = player.first_name || "";
    form.last_name.value = player.last_name || "";
    form.phone_number.value = "";
    form.email.value = "";
    playerNameHeading.textContent = player.screen_name || [player.first_name, player.last_name].filter(Boolean).join(" ") || player.initials;
    pageTitle.textContent = `Player ${player.initials}`;
    renderSummary(player);
    renderStats(player.stats);
    recordInitialSnapshot();
};

const fetchPlayer = async () => {
    if (!playerId) {
        throw new Error("Player id not found in URL");
    }

    const response = await fetch(`/api/v1/players/${playerId}`);
    if (!response.ok) {
        throw new Error("Unable to load player");
    }
    return response.json();
};

const refreshPlayer = async () => {
    setStatus("Loading player…", "info");
    try {
        const player = await fetchPlayer();
        populateForm(player);
        setStatus("Player loaded.", "success");
    } catch (error) {
        setStatus(error.message, "error");
    }
};

const handleSubmit = async (event) => {
    event.preventDefault();
    if (!form.reportValidity()) {
        setStatus("Please complete required fields.", "error");
        return;
    }

    if (!hasContact()) {
        setStatus("Add a phone number or email to save.", "error");
        return;
    }
    const payload = serializeForm(form);

    setStatus("Saving changes…", "info");

    try {
        const response = await fetch(`/api/v1/players/${playerId}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(formatErrorDetail(error.detail));
        }

        const player = await response.json();
        populateForm(player);
        recordInitialSnapshot();
        setStatus("Saved!", "success");
    } catch (error) {
        setStatus(error.message, "error");
    }
};

const showEditor = () => {
    isEditing = true;
    editPanel.hidden = false;
    editButton.setAttribute("aria-expanded", "true");
    editButton.textContent = "Editing";
    updateSaveButtonState();
};

editButton.addEventListener("click", showEditor);
form.addEventListener("submit", handleSubmit);
form.addEventListener("input", updateSaveButtonState);

document.addEventListener("DOMContentLoaded", refreshPlayer);
