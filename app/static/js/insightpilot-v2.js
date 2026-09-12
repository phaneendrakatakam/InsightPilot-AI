(() => {
  "use strict";

  const API_ENDPOINT = "/api/v2/investigate";
  const LATEST_KEY = "insightpilot:v2:latest";
  const HISTORY_KEY = "insightpilot:v2:history";
  const MAX_HISTORY = 10;
  const HISTORY_ROW_CAP = 25;

  const form = document.getElementById("investigateForm");
  const input = document.getElementById("questionInput");
  const button = document.getElementById("investigateButton");
  const charCounter = document.getElementById("charCounter");

  const workspace = document.getElementById("workspace");
  const workspaceQuestion = document.getElementById("workspaceQuestion");
  const reportStatus = document.getElementById("reportStatus");
  const restoredChip = document.getElementById("restoredChip");
  const newInvestigationButton = document.getElementById("newInvestigationButton");

  const thinkingPanel = document.getElementById("thinkingPanel");
  const thinkingTitle = document.getElementById("thinkingTitle");
  const thinkingDetail = document.getElementById("thinkingDetail");
  const thinkingMeter = document.getElementById("thinkingMeter");

  const report = document.getElementById("report");
  const conclusionText = document.getElementById("conclusionText");
  const findingsGrid = document.getElementById("findingsGrid");
  const investigationTrail = document.getElementById("investigationTrail");
  const trailMeta = document.getElementById("trailMeta");
  const caveatsPanel = document.getElementById("caveatsPanel");
  const caveatsList = document.getElementById("caveatsList");

  const errorState = document.getElementById("errorState");
  const errorMessage = document.getElementById("errorMessage");

  const historyButton = document.getElementById("historyButton");
  const historyCount = document.getElementById("historyCount");
  const historyDrawer = document.getElementById("historyDrawer");
  const historyBackdrop = document.getElementById("historyBackdrop");
  const closeHistoryButton = document.getElementById("closeHistoryButton");
  const historyList = document.getElementById("historyList");
  const clearHistoryButton = document.getElementById("clearHistoryButton");

  const toast = document.getElementById("toast");
  const suggestions = [...document.querySelectorAll(".suggestion")];

  let isBusy = false;
  let thinkingTimer = null;

  const thinkingSteps = [
    ["Planning the investigation", "Breaking the question into evidence-gathering steps..."],
    ["Selecting evidence domains", "Mapping each step to approved business tables..."],
    ["Generating read-only SQL", "Creating one safe PostgreSQL query per evidence signal..."],
    ["Validating query safety", "Checking table scope, read-only rules, and row limits..."],
    ["Collecting live evidence", "Executing each validated query against PostgreSQL..."],
    ["Synthesizing findings", "Ranking the strongest evidence-backed signals..."],
  ];

  function safeParse(raw, fallback) {
    if (!raw) return fallback;
    try {
      return JSON.parse(raw);
    } catch (_) {
      return fallback;
    }
  }

  function storageGet(key, fallback) {
    try {
      return safeParse(window.localStorage.getItem(key), fallback);
    } catch (_) {
      return fallback;
    }
  }

  function storageSet(key, value) {
    try {
      window.localStorage.setItem(key, JSON.stringify(value));
      return true;
    } catch (_) {
      return false;
    }
  }

  function storageRemove(key) {
    try {
      window.localStorage.removeItem(key);
    } catch (_) {
      // Browser storage can be unavailable in privacy-restricted contexts.
    }
  }

  function showToast(message) {
    toast.textContent = message;
    toast.classList.add("is-visible");
    window.clearTimeout(showToast.timer);
    showToast.timer = window.setTimeout(() => {
      toast.classList.remove("is-visible");
    }, 1900);
  }

  function autoResize() {
    input.style.height = "auto";
    input.style.height = `${Math.min(input.scrollHeight, 170)}px`;
    charCounter.textContent = `${input.value.length} / 1000`;
  }

  function setBusy(value) {
    isBusy = value;
    button.disabled = value;
    input.disabled = value;
    button.classList.toggle("is-loading", value);
  }

  function showWorkspace(question) {
    workspace.classList.add("is-visible");
    workspace.setAttribute("aria-hidden", "false");
    workspaceQuestion.textContent = question;
    document.body.classList.add("has-report");

    window.setTimeout(() => {
      workspace.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 150);
  }

  function resetWorkspaceState() {
    stopThinking();
    report.hidden = true;
    errorState.hidden = true;
    restoredChip.hidden = true;
  }

  function startThinking() {
    stopThinking();

    let index = 0;
    thinkingPanel.hidden = false;
    thinkingTitle.textContent = thinkingSteps[0][0];
    thinkingDetail.textContent = thinkingSteps[0][1];
    thinkingMeter.style.width = `${100 / thinkingSteps.length}%`;

    thinkingTimer = window.setInterval(() => {
      index = (index + 1) % thinkingSteps.length;
      thinkingTitle.textContent = thinkingSteps[index][0];
      thinkingDetail.textContent = thinkingSteps[index][1];
      thinkingMeter.style.width = `${((index + 1) / thinkingSteps.length) * 100}%`;

      [thinkingTitle, thinkingDetail].forEach((element) => {
        element.animate(
          [
            { opacity: 0, transform: "translateY(4px)" },
            { opacity: 1, transform: "translateY(0)" },
          ],
          { duration: 280, easing: "ease-out" }
        );
      });
    }, 1200);
  }

  function stopThinking() {
    if (thinkingTimer) {
      window.clearInterval(thinkingTimer);
      thinkingTimer = null;
    }
    thinkingPanel.hidden = true;
  }

  function statusText(status) {
    const normalized = (status || "completed").toLowerCase();
    if (normalized === "partial") return "Partial";
    if (normalized === "failed") return "Failed";
    return "Completed";
  }

  function setReportStatus(status) {
    const normalized = (status || "completed").toLowerCase();
    reportStatus.textContent = statusText(normalized);
    reportStatus.dataset.status = normalized;
  }

  function significanceRank(value) {
    return { high: 0, medium: 1, low: 2 }[(value || "").toLowerCase()] ?? 3;
  }

  function renderFindings(findings = []) {
    findingsGrid.innerHTML = "";

    const sorted = [...findings].sort(
      (a, b) => significanceRank(a.significance) - significanceRank(b.significance)
    );

    if (!sorted.length) {
      const empty = document.createElement("article");
      empty.className = "finding-card";
      empty.innerHTML = `
        <div class="finding-card__top">
          <span class="finding-card__index">00</span>
          <span class="significance significance--low">No ranked signal</span>
        </div>
        <h4>No ranked findings were returned</h4>
        <p>The investigation completed without additional significance-ranked findings.</p>
      `;
      findingsGrid.appendChild(empty);
      return;
    }

    sorted.forEach((finding, index) => {
      const significance = (finding.significance || "low").toLowerCase();
      const card = document.createElement("article");
      card.className = "finding-card";

      const top = document.createElement("div");
      top.className = "finding-card__top";

      const number = document.createElement("span");
      number.className = "finding-card__index";
      number.textContent = String(index + 1).padStart(2, "0");

      const badge = document.createElement("span");
      badge.className = `significance significance--${significance}`;
      badge.textContent = significance;

      top.append(number, badge);

      const title = document.createElement("h4");
      title.textContent = finding.title || "Finding";

      const evidence = document.createElement("p");
      evidence.textContent = finding.evidence || "No evidence summary was returned.";

      card.append(top, title, evidence);
      findingsGrid.appendChild(card);
    });
  }

  function formatCell(value) {
    if (value === null || value === undefined) return "—";
    if (typeof value === "object") return JSON.stringify(value);
    return String(value);
  }

  function buildEvidenceTable(rows = []) {
    if (!rows.length) {
      const empty = document.createElement("div");
      empty.className = "raw-evidence";
      empty.innerHTML = '<div style="padding:12px;color:#6d879a;font-size:10px;">No raw rows returned.</div>';
      return empty;
    }

    const columns = [...new Set(rows.flatMap((row) => Object.keys(row)))];
    const wrapper = document.createElement("div");
    wrapper.className = "raw-evidence";

    const table = document.createElement("table");
    const thead = document.createElement("thead");
    const tbody = document.createElement("tbody");

    const header = document.createElement("tr");
    columns.forEach((column) => {
      const th = document.createElement("th");
      th.textContent = column.replaceAll("_", " ");
      header.appendChild(th);
    });
    thead.appendChild(header);

    rows.forEach((row) => {
      const tr = document.createElement("tr");
      columns.forEach((column) => {
        const td = document.createElement("td");
        td.textContent = formatCell(row[column]);
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });

    table.append(thead, tbody);
    wrapper.appendChild(table);
    return wrapper;
  }

  function buildStepCard(step, index) {
    const card = document.createElement("article");
    card.className = "step-card";

    const summary = document.createElement("button");
    summary.className = "step-card__summary";
    summary.type = "button";
    summary.setAttribute("aria-expanded", "false");

    const number = document.createElement("span");
    number.className = "step-card__number";
    number.textContent = String(index + 1).padStart(2, "0");

    const copy = document.createElement("span");
    copy.className = "step-card__copy";

    const title = document.createElement("strong");
    title.textContent = step.title || `Investigation step ${index + 1}`;

    const objective = document.createElement("p");
    objective.textContent = step.objective || "";

    copy.append(title, objective);

    const meta = document.createElement("span");
    meta.className = "step-card__meta";

    const status = document.createElement("span");
    status.className = "step-status";
    status.dataset.status = step.status || "completed";
    status.textContent = step.status || "completed";

    const chevron = document.createElement("span");
    chevron.className = "step-card__chevron";
    chevron.textContent = "⌄";

    meta.append(status, chevron);
    summary.append(number, copy, meta);

    const body = document.createElement("div");
    body.className = "step-card__body";

    const evidence = document.createElement("p");
    evidence.className = step.error ? "step-error" : "step-evidence";
    evidence.textContent =
      step.error ||
      step.evidence_summary ||
      "No evidence summary was returned for this step.";
    body.appendChild(evidence);

    const detailGrid = document.createElement("div");
    detailGrid.className = "step-detail-grid";

    const tablesBox = document.createElement("div");
    tablesBox.className = "detail-box";
    const tablesLabel = document.createElement("small");
    tablesLabel.textContent = "Approved tables";
    const pills = document.createElement("div");
    pills.className = "table-pills";

    (step.tables || []).forEach((table) => {
      const pill = document.createElement("span");
      pill.className = "table-pill";
      pill.textContent = table;
      pills.appendChild(pill);
    });

    if (!(step.tables || []).length) {
      const none = document.createElement("span");
      none.className = "table-pill";
      none.textContent = "none";
      pills.appendChild(none);
    }

    tablesBox.append(tablesLabel, pills);

    const rowsBox = document.createElement("div");
    rowsBox.className = "detail-box";
    const rowsLabel = document.createElement("small");
    rowsLabel.textContent = "Returned rows";
    const rowsValue = document.createElement("span");
    rowsValue.className = "rows-label";
    rowsValue.textContent =
      step.row_count === null || step.row_count === undefined
        ? "—"
        : String(step.row_count);

    rowsBox.append(rowsLabel, rowsValue);
    detailGrid.append(tablesBox, rowsBox);
    body.appendChild(detailGrid);

    if (step.sql) {
      const sqlBlock = document.createElement("div");
      sqlBlock.className = "sql-block";

      const bar = document.createElement("div");
      bar.className = "sql-block__bar";
      const barLabel = document.createElement("span");
      barLabel.textContent = "PostgreSQL · validated read-only";
      const copyButton = document.createElement("button");
      copyButton.className = "copy-sql";
      copyButton.type = "button";
      copyButton.textContent = "Copy SQL";

      copyButton.addEventListener("click", async (event) => {
        event.stopPropagation();
        try {
          await navigator.clipboard.writeText(step.sql);
          showToast("SQL copied");
        } catch (_) {
          showToast("Could not copy SQL");
        }
      });

      bar.append(barLabel, copyButton);

      const pre = document.createElement("pre");
      const code = document.createElement("code");
      code.textContent = step.sql;
      pre.appendChild(code);

      sqlBlock.append(bar, pre);
      body.appendChild(sqlBlock);
    }

    body.appendChild(buildEvidenceTable(step.rows || []));

    summary.addEventListener("click", () => {
      const open = card.classList.toggle("is-open");
      summary.setAttribute("aria-expanded", String(open));
    });

    card.append(summary, body);
    return card;
  }

  function renderTrail(plan) {
    investigationTrail.innerHTML = "";

    const steps = plan?.steps || [];
    const completed = steps.filter((step) => step.status === "completed").length;
    trailMeta.textContent = `${completed}/${steps.length} evidence steps completed`;

    steps.forEach((step, index) => {
      investigationTrail.appendChild(buildStepCard(step, index));
    });
  }

  function renderCaveats(caveats = []) {
    caveatsList.innerHTML = "";

    if (!caveats.length) {
      caveatsPanel.hidden = true;
      return;
    }

    caveats.forEach((caveat) => {
      const li = document.createElement("li");
      li.textContent = caveat;
      caveatsList.appendChild(li);
    });

    caveatsPanel.hidden = false;
  }

  function renderReport(payload, { restored = false } = {}) {
    resetWorkspaceState();

    showWorkspace(payload.question || "Investigation");
    setReportStatus(payload.status || "completed");
    restoredChip.hidden = !restored;

    conclusionText.textContent =
      payload.conclusion ||
      "The investigation completed without a synthesized conclusion.";

    renderFindings(payload.findings || []);
    renderTrail(payload.plan || {});
    renderCaveats(payload.caveats || []);

    report.hidden = false;

    document.querySelectorAll(".report-enter").forEach((element) => {
      element.style.animation = "none";
      element.offsetHeight;
      element.style.animation = "";
    });
  }

  function renderError(message) {
    stopThinking();
    report.hidden = true;
    errorMessage.textContent =
      message || "InsightPilot could not complete this investigation.";
    errorState.hidden = false;
  }

  function makeHistorySnapshot(payload) {
    return {
      ...payload,
      plan: payload.plan
        ? {
            ...payload.plan,
            steps: (payload.plan.steps || []).map((step) => ({
              ...step,
              rows: (step.rows || []).slice(0, HISTORY_ROW_CAP),
            })),
          }
        : payload.plan,
      _history_snapshot: true,
    };
  }

  function persistReport(payload) {
    const record = {
      id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
      saved_at: new Date().toISOString(),
      payload,
    };

    storageSet(LATEST_KEY, record);

    const history = storageGet(HISTORY_KEY, []);
    const snapshotRecord = {
      ...record,
      payload: makeHistorySnapshot(payload),
    };

    const nextHistory = [
      snapshotRecord,
      ...history.filter((item) => item?.payload?.question !== payload.question),
    ].slice(0, MAX_HISTORY);

    // If the browser storage limit is reached, progressively trim older entries.
    let saved = false;
    let candidate = nextHistory;

    while (!saved && candidate.length) {
      saved = storageSet(HISTORY_KEY, candidate);
      if (!saved) candidate = candidate.slice(0, -1);
    }

    refreshHistory();
  }

  function clearCurrent() {
    storageRemove(LATEST_KEY);
  }

  function formatSavedAt(value) {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "Saved investigation";

    return date.toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  }

  function refreshHistory() {
    const history = storageGet(HISTORY_KEY, []);
    historyCount.textContent = String(history.length);
    historyList.innerHTML = "";

    if (!history.length) {
      const empty = document.createElement("div");
      empty.className = "history-empty";
      empty.textContent = "No saved investigations yet.";
      historyList.appendChild(empty);
      return;
    }

    history.forEach((record) => {
      const payload = record.payload || {};
      const item = document.createElement("button");
      item.type = "button";
      item.className = "history-item";

      const timestamp = document.createElement("small");
      timestamp.textContent = formatSavedAt(record.saved_at);

      const question = document.createElement("strong");
      question.textContent = payload.question || "Investigation";

      const conclusion = document.createElement("p");
      conclusion.textContent =
        payload.conclusion || "Saved investigation snapshot";

      item.append(timestamp, question, conclusion);

      item.addEventListener("click", () => {
        closeHistory();
        storageSet(LATEST_KEY, record);
        renderReport(payload, { restored: true });
      });

      historyList.appendChild(item);
    });
  }

  function openHistory() {
    refreshHistory();
    historyDrawer.classList.add("is-open");
    historyDrawer.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";
  }

  function closeHistory() {
    historyDrawer.classList.remove("is-open");
    historyDrawer.setAttribute("aria-hidden", "true");
    document.body.style.overflow = "";
  }

  async function submitInvestigation(question) {
    const cleanQuestion = (question || "").trim();
    if (!cleanQuestion || isBusy) return;

    input.value = cleanQuestion;
    autoResize();
    clearCurrent();
    resetWorkspaceState();
    showWorkspace(cleanQuestion);
    setBusy(true);
    startThinking();

    try {
      const response = await fetch(API_ENDPOINT, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: cleanQuestion }),
      });

      let payload = null;

      try {
        payload = await response.json();
      } catch (_) {
        payload = null;
      }

      stopThinking();

      if (!response.ok) {
        const detail =
          typeof payload?.detail === "string"
            ? payload.detail
            : "InsightPilot could not process this investigation.";
        renderError(detail);
        return;
      }

      if (!payload || !["completed", "partial", "failed"].includes(payload.status)) {
        renderError("InsightPilot returned an unexpected investigation response.");
        return;
      }

      renderReport(payload);
      persistReport(payload);
    } catch (error) {
      renderError(
        "The UI could not reach the V2 investigation API. Confirm that FastAPI is running."
      );
      console.error(error);
    } finally {
      setBusy(false);
    }
  }

  function beginNewInvestigation() {
    clearCurrent();
    resetWorkspaceState();

    workspace.classList.remove("is-visible");
    workspace.setAttribute("aria-hidden", "true");
    document.body.classList.remove("has-report");

    input.value = "";
    autoResize();

    window.scrollTo({ top: 0, behavior: "smooth" });
    window.setTimeout(() => input.focus(), 360);
  }

  function restoreLatest() {
    const record = storageGet(LATEST_KEY, null);
    if (!record?.payload) return;

    input.value = record.payload.question || "";
    autoResize();
    renderReport(record.payload, { restored: true });
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    submitInvestigation(input.value);
  });

  input.addEventListener("input", autoResize);
  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      form.requestSubmit();
    }
  });

  suggestions.forEach((suggestion) => {
    suggestion.addEventListener("click", () => {
      submitInvestigation(suggestion.dataset.question || "");
    });
  });

  newInvestigationButton.addEventListener("click", beginNewInvestigation);

  historyButton.addEventListener("click", openHistory);
  closeHistoryButton.addEventListener("click", closeHistory);
  historyBackdrop.addEventListener("click", closeHistory);

  clearHistoryButton.addEventListener("click", () => {
    storageRemove(HISTORY_KEY);
    refreshHistory();
    showToast("History cleared");
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && historyDrawer.classList.contains("is-open")) {
      closeHistory();
    }
  });

  autoResize();
  refreshHistory();
  restoreLatest();
})();
