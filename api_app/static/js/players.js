const rosterList = document.getElementById("roster-list");
const statusBanner = document.getElementById("status-banner");
const emptyCopy = document.getElementById("empty-copy");
const searchInput = document.getElementById("search");

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

const createPlayerCard = (player) => {
    const link = document.createElement("a");
    link.className = "list__item list__item--interactive";
    link.href = `/players/${player.id}`;
    link.role = "listitem";

    const header = document.createElement("div");
    header.className = "list__item__header";

    const initials = document.createElement("div");
    initials.className = "badge";
    initials.textContent = player.initials || "---";

    const nameBlock = document.createElement("div");
    nameBlock.className = "list__item__title";

    const name = document.createElement("strong");
    const screenName = player.screen_name ? ` (${player.screen_name})` : "";
    const fullName = [player.first_name, player.last_name].filter(Boolean).join(" ");
    name.textContent = fullName || player.screen_name || "Unnamed player";

    const subtitle = document.createElement("p");
    subtitle.className = "hint";
    subtitle.textContent = screenName || "View stats & edit";

    nameBlock.appendChild(name);
    nameBlock.appendChild(subtitle);

    header.appendChild(initials);
    header.appendChild(nameBlock);

    link.appendChild(header);

    return link;
};

const renderPlayers = (players) => {
    rosterList.innerHTML = "";

    if (!players.length) {
        emptyCopy.textContent = "No players yet. Add some to get rolling.";
        rosterList.appendChild(emptyCopy);
        return;
    }

    players
        .sort((a, b) => (a.initials || "").localeCompare(b.initials || ""))
        .forEach((player) => {
            const card = createPlayerCard(player);
            rosterList.appendChild(card);
        });
};

const loadPlayers = async (searchTerm = "") => {
    setStatus("Loading players…", "info");
    emptyCopy.textContent = "Loading players…";
    try {
        const params = new URLSearchParams();
        if (searchTerm) {
            params.set("search", searchTerm);
        }
        const response = await fetch(`/api/v1/players/${params.size ? `?${params.toString()}` : ""}`);
        if (!response.ok) {
            throw new Error("Unable to load players");
        }
        const players = await response.json();
        renderPlayers(players);
        setStatus(players.length ? "" : "No players found.", players.length ? "info" : "error");
    } catch (error) {
        setStatus(error.message, "error");
        emptyCopy.textContent = "Could not load players.";
    }
};

const handleSearch = (event) => {
    const term = event.target.value;
    loadPlayers(term);
};

searchInput.addEventListener("input", handleSearch);

loadPlayers();
