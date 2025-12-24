(() => {
  const leaderboardEl = document.getElementById("leaderboard");
  const boardShellEl = document.querySelector(".board-shell");
  const boardSurfaceEl = document.querySelector(".board-surface");
  const liveGamesEl = document.getElementById("live-games");
  const SUMMARY_URL = "/api/v1/leaderboard/summary";
  const LIVE_URL = "/api/v1/games/live";
  const REFRESH_MS = 15000;
  const LIVE_REFRESH_MS = 2000;
  const TITLE_ROTATE_MS = 12000;
  const LIVE_PAGE_MS = 9000;
  const MAX_VISIBLE_LIVE = 4;
  const CARDS_PER_PAGE = 6;
  const WINDOW_ORDER = ["all-time", "year", "month", "week", "24h"];
  // Adjust display weighting here; higher numbers surface more frequently.
  const PRIORITY_RULES = {
    leaderboard: {
      hot: 9,
      active: 6,
      stale: 3,
    },
    tournament: {
      active: 8,
      upcoming: 6,
      recent: 4,
    },
  };
  let refreshTimer = null;
  let rotationTimer = null;
  let liveTimer = null;
  let liveTimeTimer = null;
  let livePageTimer = null;
  let hasLiveGames = false;
  let livePages = [];
  let livePageIndex = 0;
  let cardEntries = [];
  let boardSchedule = [];
  let boardPages = [];
  let boardCursor = 0;
  let carouselTrackEl = null;
  const liveScoreMemory = new Map();

  function formatScore(value) {
    const num = Number(value || 0);
    const abs = Math.abs(num);
    const suffixes = [
      { limit: 1_000_000_000_000, suffix: "T" },
      { limit: 1_000_000_000, suffix: "B" },
      { limit: 1_000_000, suffix: "M" },
      { limit: 1_000, suffix: "K" },
    ];

    for (const { limit, suffix } of suffixes) {
      if (abs >= limit) {
        const short = num / limit;
        const digits = short >= 100 ? 0 : short >= 10 ? 1 : 2;
        const formatted = short.toFixed(digits).replace(/\.0+$|(?<=\.\d)0+$/, "");
        return `${formatted}${suffix}`;
      }
    }

    return num.toLocaleString();
  }

  function formatLiveScore(value) {
    const num = Number(value || 0);
    if (Number.isNaN(num)) return "0";
    return num.toLocaleString();
  }

  function formatBallScore(value) {
    return formatScore(value);
  }

  function formatDateOnly(value) {
    const date = value ? new Date(value) : null;
    if (!date) return "";
    return date.toLocaleDateString([], {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  }

  function clearChildren(node) {
    while (node.firstChild) {
      node.removeChild(node.firstChild);
    }
  }

  function getPlayerKey(gameId, entry) {
    const playerId =
      entry.player_id || entry.player_number || entry.initials || entry.screen_name || "unknown";
    return `${gameId || "game"}:${playerId}`;
  }

  function animateCount(node, key, nextValue, { duration = 800, formatter }) {
    const target = Number(nextValue) || 0;
    const previous = liveScoreMemory.get(key);
    const startValue = Number.isFinite(previous?.actual) ? previous.actual : target;

    if (previous?.rafId) {
      cancelAnimationFrame(previous.rafId);
    }

    if (startValue === target) {
      node.textContent = formatter(target);
      liveScoreMemory.set(key, { actual: target });
      return;
    }

    const startTime = performance.now();

    const step = (now) => {
      const progress = Math.min((now - startTime) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = Math.round(startValue + (target - startValue) * eased);
      node.textContent = formatter(current);

      if (progress < 1) {
        const rafId = requestAnimationFrame(step);
        liveScoreMemory.set(key, { actual: target, rafId });
      } else {
        liveScoreMemory.set(key, { actual: target });
      }
    };

    const rafId = requestAnimationFrame(step);
    liveScoreMemory.set(key, { actual: startValue, rafId });
  }

  function applyCountUp(node, key, nextValue, { duration = 800, abbreviate = true } = {}) {
    const formatter = abbreviate ? formatScore : formatLiveScore;
    animateCount(node, key, nextValue, { duration, formatter });
  }

  function formatDuration(seconds) {
    const total = Math.max(0, Number(seconds) || 0);
    const mins = Math.floor(total / 60);
    const secs = total % 60;
    if (mins >= 60) {
      const hours = Math.floor(mins / 60);
      const remMins = mins % 60;
      return `${hours}h ${remMins}m`;
    }
    if (mins > 0) {
      return `${mins}m ${secs.toString().padStart(2, "0")}s`;
    }
    return `${secs}s`;
  }

  function computeLiveSeconds(baseSeconds, updatedAtMs) {
    const base = Number(baseSeconds) || 0;
    const updatedAt = Number(updatedAtMs) || Date.now();
    const deltaSeconds = (Date.now() - updatedAt) / 1000;
    return Math.max(0, Math.floor(base + deltaSeconds));
  }

  function formatClock(seconds) {
    const total = Math.max(0, Number(seconds) || 0);
    const minutes = Math.floor(total / 60);
    const secs = total % 60;
    return `${minutes}:${secs.toString().padStart(2, "0")}`;
  }

  function updateLiveTimes() {
    const timeNodes = document.querySelectorAll(
      ".live-card__time, .live-score__ball-time"
    );
    timeNodes.forEach((node) => {
      const isLive = node.dataset.live === "true";
      const nextSeconds = isLive
        ? computeLiveSeconds(node.dataset.baseSeconds, node.dataset.updatedAt)
        : Math.max(0, Number(node.dataset.baseSeconds) || 0);
      node.textContent = formatClock(nextSeconds);
    });
  }

  function buildPlayerRow(entry, index) {
    const item = document.createElement("li");
    item.className = "list__item c-list__item";

    const placement = document.createElement("div");
    placement.className = "placement c-list__cell";
    placement.textContent = `#${index + 1}`;

    const player = document.createElement("div");
    player.className = "player c-list__cell";

    const screenName = document.createElement("p");
    screenName.className = "player__name rank c-chip";
    screenName.textContent = entry.screen_name || "Unnamed player";

    player.append(screenName);

    const score = document.createElement("div");
    score.className = "score c-list__cell c-list__cell--value";
    const scoreValue = document.createElement("div");
    scoreValue.className = "score__value c-list__value";
    scoreValue.textContent = formatScore(entry.score);

    const scoreDate = document.createElement("div");
    scoreDate.className = "score__date c-list__note";
    scoreDate.textContent = entry.last_played ? formatDateOnly(entry.last_played) : "—";

    score.append(scoreValue, scoreDate);

    item.append(placement, player, score);
    return item;
  }

  function buildLiveScore(entry, receivedAt, gameId) {
    const row = document.createElement("div");
    row.className = "live-score";
    if (entry.is_player_up) {
      row.classList.add("live-score--active");
    }

    const playerKey = getPlayerKey(gameId, entry);
    const name = document.createElement("p");
    name.className = "live-score__name";
    name.classList.add(entry.is_player_up ? "live-score__name--active" : "live-score__name--idle");
    name.textContent = entry.screen_name || entry.initials || "Player";

    const value = document.createElement("div");
    value.className = "live-score__value";
    applyCountUp(value, playerKey, entry.score, { abbreviate: false, duration: 1200 });

    const balls = document.createElement("div");
    balls.className = "live-score__balls";

    if (entry.ball_times?.length) {
      entry.ball_times.forEach((item) => {
        const chip = document.createElement("div");
        chip.className = "live-score__ball";
        if (item.is_current) {
          chip.classList.add("live-score__ball--current");
        }

        const label = document.createElement("span");
        label.className = "live-score__ball-label";
        label.textContent = `B${item.ball}`;

        const ballKey = `${playerKey}-ball-${item.ball}`;
        const ballScore = document.createElement("span");
        ballScore.className = "live-score__ball-score";
        applyCountUp(ballScore, ballKey, item.score, { duration: 700, abbreviate: true });

        const ballTime = document.createElement("span");
        ballTime.className = "live-score__ball-time live-card__time";
        ballTime.dataset.baseSeconds = item.seconds || 0;
        ballTime.dataset.updatedAt = receivedAt;
        ballTime.dataset.live = item.is_current ? "true" : "false";
        ballTime.textContent = formatClock(item.seconds || 0);

        chip.append(label, ballScore, ballTime);
        balls.append(chip);
      });
    }

    row.append(name, value, balls);
    return row;
  }

  function buildLiveBadge() {
    const badge = document.createElement("span");
    badge.className = "live-card__badge";

    const dot = document.createElement("span");
    dot.className = "live-card__badge-dot";
    dot.setAttribute("aria-hidden", "true");

    const label = document.createElement("span");
    label.textContent = "Live";

    badge.append(dot, label);
    return badge;
  }

  function buildLiveCard(game, receivedAt) {
    const card = document.createElement("article");
    card.className = "live-card c-card c-card--window";

    const header = document.createElement("div");
    header.className = "live-card__header";

    const identity = document.createElement("div");
    identity.className = "live-card__identity";

    const title = document.createElement("h3");
    title.className = "live-card__title";
    title.textContent = game.machine_name || game.machine_uid || "Unknown machine";

    const meta = document.createElement("p");
    meta.className = "live-card__meta";
    meta.textContent = game.machine_ip || "Unknown IP";

    identity.append(title, meta);

    header.append(identity, buildLiveBadge());

    const scores = document.createElement("div");
    scores.className = "live-card__scores";

    if (!game.scores?.length) {
      const empty = document.createElement("div");
      empty.className = "live-card__empty";
      empty.textContent = "Waiting for scores…";
      scores.append(empty);
    } else {
      game.scores.forEach((entry) => {
        scores.append(buildLiveScore(entry, receivedAt, game.game_id));
      });
    }

    card.append(header, scores);
    return card;
  }

  function buildEmptyState(message) {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = message;
    return empty;
  }

  function buildList(entries) {
    const container = document.createElement("div");
    container.className = "list c-list";

    const list = document.createElement("ul");
    list.className = "list__body c-list__body";

    entries.forEach((entry, index) => {
      list.appendChild(buildPlayerRow(entry, index));
    });

    container.append(list);
    return container;
  }

  function buildTournamentRow(entry, index) {
    const item = document.createElement("li");
    item.className = "list__item c-list__item";

    const placement = document.createElement("div");
    placement.className = "placement c-list__cell";
    placement.textContent = `#${index + 1}`;

    const player = document.createElement("div");
    player.className = "player c-list__cell";

    const screenName = document.createElement("p");
    screenName.className = "player__name rank c-chip";
    screenName.textContent = entry.screen_name || entry.initials || "Unnamed player";

    player.append(screenName);

    const score = document.createElement("div");
    score.className = "score c-list__cell c-list__cell--value";
    const scoreValue = document.createElement("div");
    scoreValue.className = "score__value c-list__value";
    scoreValue.textContent = formatScore(entry.score);

    const scoreDate = document.createElement("div");
    scoreDate.className = "score__date c-list__note";
    scoreDate.textContent = entry.last_played ? formatDateOnly(entry.last_played) : "—";

    score.append(scoreValue, scoreDate);

    item.append(placement, player, score);
    return item;
  }

  function buildTournamentList(entries) {
    const container = document.createElement("div");
    container.className = "list c-list";

    const list = document.createElement("ul");
    list.className = "list__body c-list__body";

    entries.forEach((entry, index) => {
      list.appendChild(buildTournamentRow(entry, index));
    });

    container.append(list);
    return container;
  }

  function buildCardHeader(gameTitle, boardTitle, metaText) {
    const header = document.createElement("div");
    header.className = "card__header c-card__header";

    const titleGroup = document.createElement("div");
    titleGroup.className = "card__title-group";

    const eyebrow = document.createElement("p");
    eyebrow.className = "card__eyebrow";
    eyebrow.textContent = gameTitle || "Featured";

    const title = document.createElement("h2");
    title.className = "card__title c-card__title";
    title.textContent = boardTitle || "Leaderboard";

    titleGroup.append(eyebrow, title);
    header.append(titleGroup);

    if (metaText) {
      const meta = document.createElement("p");
      meta.className = "card__meta";
      meta.textContent = metaText;
      header.append(meta);
    }

    return header;
  }

  function buildWindowCard(board) {
    const card = document.createElement("article");
    card.className = "card card--window c-card c-card--window";

    const header = buildCardHeader(board.game_name, board.window_label || board.title);

    const list = buildList(board.leaderboard || []);

    card.append(header, list);
    return card;
  }

  function formatTournamentWindow(tournament) {
    const { start_time: startTime, end_time: endTime, display_until: displayUntil } = tournament;
    if (!startTime && !endTime) return "No schedule";

    const formatOptions = { month: "short", day: "numeric" };
    const start = startTime ? new Date(startTime).toLocaleDateString([], formatOptions) : null;
    const end = endTime ? new Date(endTime).toLocaleDateString([], formatOptions) : null;
    const display = displayUntil
      ? new Date(displayUntil).toLocaleDateString([], { ...formatOptions, hour: "2-digit", minute: "2-digit" })
      : null;

    if (start && end) {
      return `${start} – ${end}${display ? ` (visible until ${display})` : ""}`;
    }
    if (start) return `Starts ${start}${display ? ` · visible until ${display}` : ""}`;
    return `Ends ${end}${display ? ` · visible until ${display}` : ""}`;
  }

  function buildTournamentCard(tournament, statusLabel) {
    const card = document.createElement("article");
    card.className = "card card--window card--tournament c-card c-card--window";

    const modeLabel = tournament.game_mode?.name ? ` · Mode: ${tournament.game_mode.name}` : "";
    const header = buildCardHeader(
      tournament.name,
      statusLabel || (tournament.is_active ? "Active tournament" : "Tournament"),
      `${tournament.scoring_profile?.name || "Custom scoring"}${modeLabel}`
    );

    const window = document.createElement("p");
    window.className = "card__meta";
    window.textContent = formatTournamentWindow(tournament);
    header.append(window);

    const body = document.createElement("div");
    body.className = "c-card__body";

    if (!tournament.leaderboard?.length) {
      const empty = document.createElement("p");
      empty.className = "hint";
      empty.textContent = tournament.is_active
        ? "Tournament is live. Waiting for first standings."
        : "No standings yet.";
      body.append(empty);
    } else {
      body.append(buildTournamentList(tournament.leaderboard));
    }

    card.append(header, body);
    return card;
  }

  function buildChampionCard(game) {
    const card = document.createElement("article");
    card.className = "card card--champion c-card c-card--hero";

    const header = buildCardHeader(game.machine_name, "All-time champion");

    const hero = document.createElement("div");
    hero.className = "champion c-card__body";

    if (game.champion) {
      const banner = document.createElement("div");
      banner.className = "champion__banner";

      const rank = document.createElement("span");
      rank.className = "champion__rank";
      rank.textContent = "#1";

      const name = document.createElement("p");
      name.className = "champion__name";
      name.textContent = game.champion.screen_name || "Unnamed player";

      banner.append(rank, name);

      const score = document.createElement("div");
      score.className = "champion__score";
      score.textContent = formatScore(game.champion.score);

      const details = document.createElement("p");
      details.className = "champion__details";
      const date = game.champion.last_played ? formatDateOnly(game.champion.last_played) : "Date unknown";
      const championName = game.champion.screen_name || "Unnamed player";
      details.textContent = `${championName} · ${date}`;

      hero.append(banner, score, details);
    } else {
      hero.classList.add("champion--empty");
    }

    card.append(header, hero);
    return card;
  }

  function suffixFromSlug(slug) {
    const parts = slug.split("-");
    return parts[parts.length - 1];
  }

  function sortWindows(windows) {
    return [...windows].sort((a, b) => {
      const aIndex = WINDOW_ORDER.indexOf(suffixFromSlug(a.slug));
      const bIndex = WINDOW_ORDER.indexOf(suffixFromSlug(b.slug));
      return (aIndex === -1 ? WINDOW_ORDER.length : aIndex) - (bIndex === -1 ? WINDOW_ORDER.length : bIndex);
    });
  }

  function extractWindowLabel(title, gameName) {
    if (!title) return "Leaderboard";
    const prefix = `${gameName} - `;
    if (gameName && title.startsWith(prefix)) {
      return title.slice(prefix.length).trim();
    }
    return title;
  }

  function leaderboardUpdatedAt(window, game) {
    const topEntry = window.leaderboard?.[0];
    return topEntry?.last_played || game.last_activity_at || game.start_time || null;
  }

  function tournamentStatus(tournament) {
    const now = Date.now();
    const start = coerceDate(tournament.start_time)?.getTime();
    const end = coerceDate(tournament.end_time)?.getTime();
    if (tournament.is_active) return "active";
    if ((start && start > now) || (end && end > now)) return "upcoming";
    return "recent";
  }

  function getBoardViewportHeight() {
    const shell = document.getElementById("big-screen");
    if (!shell) return window.innerHeight;

    const shellStyles = getComputedStyle(shell);
    const paddingTop = parseFloat(shellStyles.paddingTop) || 0;
    const paddingBottom = parseFloat(shellStyles.paddingBottom) || 0;
    return Math.max(window.innerHeight - paddingTop - paddingBottom, 0);
  }

  function coerceDate(value) {
    if (!value) return null;
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? null : date;
  }

  function recencyWeight(updatedAt) {
    const date = coerceDate(updatedAt);
    if (!date) return 1;
    const ageMs = Date.now() - date.getTime();
    if (ageMs < 5 * 60 * 1000) return 6;
    if (ageMs < 30 * 60 * 1000) return 5;
    if (ageMs < 2 * 60 * 60 * 1000) return 4;
    if (ageMs < 12 * 60 * 60 * 1000) return 3;
    if (ageMs < 48 * 60 * 60 * 1000) return 2;
    return 1;
  }

  function leaderboardStatus(updatedAt) {
    const date = coerceDate(updatedAt);
    if (!date) return "stale";
    const ageMs = Date.now() - date.getTime();
    if (ageMs < 10 * 60 * 1000) return "hot";
    if (ageMs < 3 * 24 * 60 * 60 * 1000) return "active";
    return "stale";
  }

  function cardWeight(entry) {
    const base =
      entry.type === "tournament"
        ? PRIORITY_RULES.tournament[entry.status] || PRIORITY_RULES.tournament.recent
        : PRIORITY_RULES.leaderboard[entry.status] || PRIORITY_RULES.leaderboard.active;
    const freshness = recencyWeight(entry.updatedAt);
    return Math.max(1, base + freshness - 1);
  }

  function buildCardEntries(summary) {
    const entries = [];

    (summary.tournaments || []).forEach((tournament) => {
      const status = tournamentStatus(tournament);
      const updatedAt = tournament.last_activity_at || tournament.start_time || tournament.end_time;
      const statusLabel =
        status === "active" ? "Active tournament" : status === "upcoming" ? "Upcoming tournament" : "Tournament";

      entries.push({
        type: "tournament",
        status,
        updatedAt,
        render: () => buildTournamentCard(tournament, statusLabel),
      });
    });

    (summary.games || []).forEach((game) => {
      const sortedWindows = sortWindows(game.windows || []);
      sortedWindows.forEach((window) => {
        if (!window.leaderboard?.length) return;

        const updatedAt = leaderboardUpdatedAt(window, game);
        const status = leaderboardStatus(updatedAt);

        entries.push({
          type: "leaderboard",
          status,
          updatedAt,
          render: () =>
            buildWindowCard({
              ...window,
              game_name: game.machine_name || game.machine_uid || "Game",
              window_label: extractWindowLabel(window.title, game.machine_name),
            }),
        });
      });

      if (game.champion) {
        const updatedAt = game.champion.last_played || game.last_activity_at || game.start_time;
        entries.push({
          type: "leaderboard",
          status: leaderboardStatus(updatedAt),
          updatedAt,
          render: () => buildChampionCard(game),
        });
      }
    });

    return entries;
  }

  function buildRotationSchedule(entries) {
    const weighted = entries
      .map((entry, index) => ({
        index,
        weight: cardWeight(entry),
        updatedAt: coerceDate(entry.updatedAt)?.getTime() || 0,
      }))
      .sort((a, b) => {
        if (b.weight !== a.weight) return b.weight - a.weight;
        if (b.updatedAt !== a.updatedAt) return b.updatedAt - a.updatedAt;
        return a.index - b.index;
      });

    return weighted.map((item) => item.index);
  }

  function buildBoardPages(schedule, entries) {
    const pages = [];
    for (let i = 0; i < schedule.length; i += CARDS_PER_PAGE) {
      const indices = schedule.slice(i, i + CARDS_PER_PAGE);
      const page = document.createElement("section");
      page.className = "game-board card-page";

      const grid = document.createElement("div");
      grid.className = "board-grid board-grid--cards";
      indices.forEach((entryIndex) => {
        const entry = entries[entryIndex];
        if (!entry) return;
        grid.appendChild(entry.render());
      });

      page.appendChild(grid);
      pages.push({ node: page });
    }
    return pages;
  }

  function buildEmptyBoard(message) {
    const page = document.createElement("section");
    page.className = "game-board card-page";

    const grid = document.createElement("div");
    grid.className = "board-grid board-grid--cards";

    const champion = buildChampionCard({ machine_name: "Leaderboards", champion: null });
    grid.appendChild(champion);

    const card = document.createElement("article");
    card.className = "card c-card";
    const header = buildCardHeader("Leaderboards", "No results yet");

    const body = document.createElement("div");
    body.className = "c-card__body";

    const note = document.createElement("p");
    note.className = "hint";
    note.textContent = message;

    body.append(note, buildList([]));

    card.append(header, body);
    grid.appendChild(card);
    page.appendChild(grid);
    return page;
  }

  function mountBoardPages(pages) {
    clearChildren(leaderboardEl);

    const carousel = document.createElement("div");
    carousel.className = "card-carousel";

    const track = document.createElement("div");
    track.className = "card-carousel__track";

    pages.forEach((page, pageIndex) => {
      page.node.dataset.pageIndex = pageIndex.toString();
      track.appendChild(page.node);
    });

    carousel.appendChild(track);
    carouselTrackEl = track;

    leaderboardEl.appendChild(carousel);

    requestAnimationFrame(() => {
      leaderboardEl.classList.add("board-grid--visible");
    });
  }

  function syncBoardHeight(board) {
    if (!boardSurfaceEl) return;
    const targetHeight = getBoardViewportHeight();
    boardSurfaceEl.style.minHeight = `${targetHeight}px`;
    boardSurfaceEl.style.maxHeight = `${targetHeight}px`;
  }

  function renderLeaderboard(summary) {
    clearChildren(leaderboardEl);
    if (rotationTimer) {
      clearInterval(rotationTimer);
      rotationTimer = null;
    }

    boardPages = [];
    boardSchedule = [];
    boardCursor = 0;
    carouselTrackEl = null;

    cardEntries = buildCardEntries(summary);

    if (boardSurfaceEl) {
      boardSurfaceEl.classList.toggle("board-surface--live", hasLiveGames);
    }

    if (!cardEntries.length) {
      boardPages = [{ node: buildEmptyBoard("No scores have been recorded yet.") }];
    } else {
      const schedule = buildRotationSchedule(cardEntries);
      boardPages = buildBoardPages(schedule, cardEntries);
    }

    mountBoardPages(boardPages);
    startBoardRotation();
  }

  function markActiveBoard(pages, pageIndex) {
    const boards = pages.map((entry) => entry.node);
    const activeBoard = boards[pageIndex];
    if (!activeBoard) return;
    boards.forEach((board, boardIndex) => {
      const isActive = boardIndex === pageIndex;
      board.classList.toggle("game-board--active", isActive);
      board.setAttribute("aria-hidden", isActive ? "false" : "true");
    });

    if (carouselTrackEl) {
      carouselTrackEl.style.transform = `translateX(-${pageIndex * 100}%)`;
    }

    syncBoardHeight(activeBoard);
  }

  function startBoardRotation() {
    if (!boardPages.length) return;

    if (rotationTimer) {
      clearInterval(rotationTimer);
      rotationTimer = null;
    }

    boardSchedule = boardPages.map((_, index) => index);
    boardCursor = 0;

    markActiveBoard(boardPages, boardSchedule[boardCursor]);

    if (boardSchedule.length === 1) return;

    rotationTimer = setInterval(() => {
      boardCursor = (boardCursor + 1) % boardSchedule.length;
      markActiveBoard(boardPages, boardSchedule[boardCursor]);
    }, TITLE_ROTATE_MS);
  }

  function paginateLiveGames(liveGames) {
    const items = liveGames || [];
    if (items.length <= MAX_VISIBLE_LIVE) return [items];

    const pages = [];
    for (let i = 0; i < items.length; i += MAX_VISIBLE_LIVE) {
      pages.push(items.slice(i, i + MAX_VISIBLE_LIVE));
    }
    return pages;
  }

  function renderLivePage(receivedAt) {
    clearChildren(liveGamesEl);
    const page = livePages[livePageIndex] || [];
    const fragment = document.createDocumentFragment();
    page.forEach((game) => fragment.appendChild(buildLiveCard(game, receivedAt)));
    liveGamesEl.appendChild(fragment);
  }

  function renderLiveGames(liveGames, receivedAt) {
    if (!liveGamesEl) return;
    const wasLive = hasLiveGames;
    hasLiveGames = Boolean(liveGames?.length);
    if (boardSurfaceEl) {
      boardSurfaceEl.classList.toggle("board-surface--live", hasLiveGames);
    }
    if (boardShellEl) {
      boardShellEl.classList.toggle("board-shell--live", hasLiveGames);
    }
    if (wasLive !== hasLiveGames) {
      fetchLeaderboard();
    }

    if (livePageTimer) {
      clearInterval(livePageTimer);
      livePageTimer = null;
    }

    if (!liveGames?.length) {
      clearChildren(liveGamesEl);
      if (liveTimeTimer) {
        clearInterval(liveTimeTimer);
        liveTimeTimer = null;
      }
      return;
    }

    livePages = paginateLiveGames(liveGames);
    livePageIndex = 0;
    renderLivePage(receivedAt);

    if (livePages.length > 1) {
      livePageTimer = setInterval(() => {
        livePageIndex = (livePageIndex + 1) % livePages.length;
        renderLivePage(receivedAt);
      }, LIVE_PAGE_MS);
    }

    if (!liveTimeTimer) {
      liveTimeTimer = setInterval(updateLiveTimes, 1000);
    }
  }

  async function fetchLeaderboard() {
    try {
      const response = await fetch(SUMMARY_URL);
      if (!response.ok) {
        throw new Error(`Failed to load leaderboard (${response.status})`);
      }

      const data = await response.json();
      renderLeaderboard(data);
    } catch (error) {
      console.error(error);
    }
  }

  async function fetchLiveGames() {
    try {
      const response = await fetch(LIVE_URL);
      if (!response.ok) {
        throw new Error(`Failed to load live games (${response.status})`);
      }

      const data = await response.json();
      renderLiveGames(data, Date.now());
    } catch (error) {
      console.error(error);
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    boardPages = [{ node: buildEmptyBoard("Loading leaderboards…") }];
    mountBoardPages(boardPages);
    boardSchedule = [0];
    boardCursor = 0;
    markActiveBoard(boardPages, 0);

    fetchLeaderboard();
    refreshTimer = setInterval(fetchLeaderboard, REFRESH_MS);

    fetchLiveGames();
    liveTimer = setInterval(fetchLiveGames, LIVE_REFRESH_MS);

    window.addEventListener("resize", () => {
      const activeBoard = leaderboardEl.querySelector(".game-board--active");
      syncBoardHeight(activeBoard);
    });
  });
})();
