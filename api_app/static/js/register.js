const form = document.getElementById("registration-form");
const statusBanner = document.getElementById("status-banner");

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
        if (value) {
            payload[key] = value;
        }
    });
    return payload;
};

const handleSubmit = async (event) => {
    event.preventDefault();
    if (!form.reportValidity()) {
        setStatus("Please complete required fields.", "error");
        return;
    }
    setStatus("Saving player…", "info");

    const payload = serializeForm(form);

    try {
        const response = await fetch("/api/v1/players/", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(formatErrorDetail(error.detail));
        }

        const player = await response.json();
        setStatus(`Saved ${player.initials}.`, "success");
        form.reset();
    } catch (error) {
        setStatus(error.message, "error");
    }
};

form.addEventListener("submit", handleSubmit);
