(() => {
  "use strict";

  const state = {
    sessionId: null,
    session: null,
    latestResponse: null,
    chart: null,
    busy: false,
  };

  const $ = (id) => document.getElementById(id);

  const els = {
    sidebar: $("sidebar"),
    mobileMenuButton: $("mobileMenuButton"),
    newButton: $("newInvestigationButton"),
    railNewButton: $("railNewButton"),
    recentList: $("recentList"),
    refreshSessionsButton: $("refreshSessionsButton"),
    investigationsNav: $("investigationsNav"),
    evidenceNav: $("evidenceNav"),
    globalSearchForm: $("globalSearchForm"),
    globalSearchInput: $("globalSearchInput"),
    emptyState: $("emptyState"),
    conversationFeed: $("conversationFeed"),
    analysisPanel: $("analysisPanel"),
    analysisTitle: $("analysisTitle"),
    analysisStatus: $("analysisStatus"),
    trustPanel: $("trustPanel"),
    trustConfidence: $("trustConfidence"),
    trustCausality: $("trustCausality"),
    trustGovernance: $("trustGovernance"),
    trustGrounding: $("trustGrounding"),
    trustToggle: $("trustToggle"),
    trustDetails: $("trustDetails"),
    trustRationale: $("trustRationale"),
    trustCausalityNote: $("trustCausalityNote"),
    provenanceList: $("provenanceList"),
    traceBlock: $("traceBlock"),
    traceSummary: $("traceSummary"),
    kpiGrid: $("kpiGrid"),
    chartSection: $("chartSection"),
    chartTitle: $("chartTitle"),
    chartEvidence: $("chartEvidence"),
    chartCanvas: $("analysisChart"),
    findingsList: $("findingsList"),
    contextGrid: $("contextGrid"),
    evidenceSection: $("evidenceSection"),
    evidenceGrid: $("evidenceGrid"),
    viewAllEvidenceButton: $("viewAllEvidenceButton"),
    suggestedFollowups: $("suggestedFollowups"),
    followupButtons: $("followupButtons"),
    composerForm: $("composerForm"),
    composerInput: $("composerInput"),
    sendButton: $("sendButton"),
    detailTitle: $("detailTitle"),
    detailCreated: $("detailCreated"),
    detailStatus: $("detailStatus"),
    detailTurns: $("detailTurns"),
    copyResponseButton: $("copyResponseButton"),
    railEvidenceButton: $("railEvidenceButton"),
    loadingOverlay: $("loadingOverlay"),
    loadingTitle: $("loadingTitle"),
    loadingDetail: $("loadingDetail"),
    toast: $("toast"),
    investigationsDrawer: $("investigationsDrawer"),
    investigationsBackdrop: $("investigationsBackdrop"),
    closeInvestigationsButton: $("closeInvestigationsButton"),
    investigationsDrawerList: $("investigationsDrawerList"),
    drawerNewInvestigationButton: $("drawerNewInvestigationButton"),
    drawerRefreshInvestigationsButton: $("drawerRefreshInvestigationsButton"),
  };

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function formatDate(value) {
    if (!value) return "—";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return String(value);
    return new Intl.DateTimeFormat("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(date);
  }

  function formatRelative(value) {
    if (!value) return "";
    const then = new Date(value).getTime();
    const now = Date.now();
    if (Number.isNaN(then)) return "";
    const minutes = Math.max(0, Math.floor((now - then) / 60000));
    if (minutes < 1) return "just now";
    if (minutes < 60) return `${minutes} min ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours} hr ago`;
    const days = Math.floor(hours / 24);
    return `${days} day${days === 1 ? "" : "s"} ago`;
  }

  function formatPeriodLabel(value) {
    if (!value) return "";

    const text = String(value);

    // Preserve already-readable labels such as "July" or "August".
    if (!/^\d{4}-\d{2}/.test(text)) return text;

    const date = new Date(text);
    if (Number.isNaN(date.getTime())) return text;

    return new Intl.DateTimeFormat("en-IN", {
      month: "short",
      year: "numeric",
    }).format(date);
  }

  function formatValue(kpi) {
    const value = Number(kpi?.value);
    if (!Number.isFinite(value)) return "—";

    if (kpi.unit === "currency") {
      return new Intl.NumberFormat("en-IN", {
        style: "currency",
        currency: "INR",
        maximumFractionDigits: value >= 100000 ? 0 : 2,
      }).format(value);
    }

    return new Intl.NumberFormat("en-IN", {
      maximumFractionDigits: 2,
    }).format(value);
  }

  function showToast(message) {
    els.toast.textContent = message;
    els.toast.classList.add("is-visible");
    window.clearTimeout(showToast.timer);
    showToast.timer = window.setTimeout(() => {
      els.toast.classList.remove("is-visible");
    }, 2200);
  }

  function setBusy(busy, title = "Investigating your question", detail = "Planning evidence, running safe SQL, and synthesizing the result…") {
    state.busy = busy;
    els.sendButton.disabled = busy;
    els.composerInput.disabled = busy;
    els.loadingTitle.textContent = title;
    els.loadingDetail.textContent = detail;
    els.loadingOverlay.hidden = !busy;
  }

  async function api(path, options = {}) {
    const response = await fetch(path, {
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
      ...options,
    });

    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      const detail = body?.detail;
      const message = typeof detail === "string"
        ? detail
        : "InsightPilot could not complete this request.";
      throw new Error(message);
    }
    return body;
  }

  function clearChart() {
    if (state.chart) {
      state.chart.destroy();
      state.chart = null;
    }
  }

  function resetWorkspace() {
    if (els.investigationsDrawer) closeInvestigationsDrawer();
    state.sessionId = null;
    state.session = null;
    state.latestResponse = null;
    clearChart();

    els.conversationFeed.innerHTML = "";
    els.analysisPanel.hidden = true;
    els.trustPanel.hidden = true;
    els.trustDetails.hidden = true;
    els.emptyState.hidden = false;
    els.kpiGrid.innerHTML = "";
    els.findingsList.innerHTML = "";
    els.contextGrid.innerHTML = "";
    els.evidenceGrid.innerHTML = "";
    els.suggestedFollowups.hidden = true;

    els.detailTitle.textContent = "New investigation";
    els.detailCreated.textContent = "—";
    els.detailStatus.textContent = "Ready";
    els.detailStatus.className = "completed-chip";
    els.detailTurns.textContent = "0";

    document.querySelectorAll(".recent-item").forEach((item) => {
      item.classList.remove("is-active");
    });

    els.composerInput.value = "";
    autosizeComposer();
    els.composerInput.focus();
  }

  async function ensureSession() {
    if (state.sessionId) return state.sessionId;

    const session = await api("/api/v3/sessions", {
      method: "POST",
      body: JSON.stringify({}),
    });

    state.sessionId = session.session_id;
    state.session = session;
    updateDetails(session, "Active");
    await refreshSessions();
    return state.sessionId;
  }

  function appendTurn(role, content, timestamp) {
    els.emptyState.hidden = true;

    const article = document.createElement("article");
    article.className = `turn turn--${role}`;
    article.innerHTML = `
      <div class="turn-avatar">${role === "user" ? "You" : "AI"}</div>
      <div class="turn-body">
        <div class="turn-meta">${role === "user" ? "You" : "InsightPilot AI"} · ${escapeHtml(formatDate(timestamp))}</div>
        <div class="turn-bubble">${escapeHtml(content)}</div>
      </div>
    `;
    els.conversationFeed.appendChild(article);
    article.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function updateDetails(session, status = "Completed") {
    if (!session) return;

    const turns = (session.messages || []).filter((m) => m.role === "user").length;
    els.detailTitle.textContent = session.title || "New investigation";
    els.detailCreated.textContent = formatDate(session.created_at);
    els.detailTurns.textContent = String(turns);
    els.detailStatus.textContent = status;
    els.detailStatus.className = "completed-chip";
    if (status === "Running") els.detailStatus.classList.add("is-running");
    if (status === "Error") els.detailStatus.classList.add("is-error");
  }

  function renderKpis(kpis = []) {
    els.kpiGrid.innerHTML = "";

    if (!kpis.length) {
      els.kpiGrid.style.display = "none";
      return;
    }

    els.kpiGrid.style.display = "grid";

    kpis.slice(0, 8).forEach((kpi) => {
      const percent = Number(kpi.percent_change);
      const hasPercent = Number.isFinite(percent);
      const direction = kpi.direction || "neutral";
      const arrow = direction === "up" ? "↑" : direction === "down" ? "↓" : direction === "flat" ? "→" : "";
      const period = [
        formatPeriodLabel(kpi.previous_period),
        formatPeriodLabel(kpi.current_period),
      ].filter(Boolean).join(" → ");

      const card = document.createElement("article");
      card.className = "kpi-card";
      card.innerHTML = `
        <span class="kpi-label">${escapeHtml(kpi.label || kpi.key)}</span>
        <strong class="kpi-value">${escapeHtml(formatValue(kpi))}</strong>
        <span class="kpi-change is-${escapeHtml(direction)}">
          ${escapeHtml(arrow)} ${hasPercent ? `${Math.abs(percent).toFixed(2)}%` : ""}
        </span>
        <span class="kpi-meta">${escapeHtml(period || (kpi.evidence_id ? `Evidence ${kpi.evidence_id}` : ""))}</span>
      `;
      els.kpiGrid.appendChild(card);
    });
  }

  function renderChart(charts = []) {
    clearChart();

    if (!charts.length || typeof window.Chart === "undefined") {
      els.chartSection.hidden = true;
      return;
    }

    const chart = charts[0];
    els.chartSection.hidden = false;
    els.chartTitle.textContent = chart.title || "Analysis trend";
    els.chartEvidence.textContent = chart.evidence_id ? `Evidence ${chart.evidence_id}` : "";

    const datasets = (chart.series || []).map((series, index) => {
      const palette = [
        ["#2768f6", "rgba(39,104,246,0.08)"],
        ["#7557f5", "rgba(117,87,245,0.06)"],
        ["#0aa678", "rgba(10,166,120,0.06)"],
      ];
      const [borderColor, backgroundColor] = palette[index % palette.length];
      return {
        label: series.label || series.key,
        data: series.values || [],
        borderColor,
        backgroundColor,
        borderWidth: 2,
        tension: 0.32,
        fill: chart.chart_type === "line" && index === 0,
        pointRadius: 2.5,
        pointHoverRadius: 4,
        borderRadius: chart.chart_type === "bar" ? 6 : 0,
      };
    });

    state.chart = new window.Chart(els.chartCanvas, {
      type: chart.chart_type || "line",
      data: {
        labels: chart.labels || [],
        datasets,
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: "index",
          intersect: false,
        },
        plugins: {
          legend: {
            position: "top",
            align: "end",
            labels: {
              usePointStyle: true,
              boxWidth: 7,
              boxHeight: 7,
              color: "#63718a",
              font: { family: "Manrope", size: 10, weight: "600" },
            },
          },
          tooltip: {
            backgroundColor: "#182640",
            titleFont: { family: "Manrope" },
            bodyFont: { family: "Manrope" },
            padding: 10,
          },
        },
        scales: {
          x: {
            grid: { color: "#edf1f6" },
            ticks: { color: "#7c899e", font: { family: "Manrope", size: 9 } },
            border: { display: false },
          },
          y: {
            beginAtZero: false,
            grid: { color: "#edf1f6" },
            ticks: {
              color: "#7c899e",
              font: { family: "Manrope", size: 9 },
              callback(value) {
                const n = Number(value);
                if (Math.abs(n) >= 1000000) return `${(n / 1000000).toFixed(1)}M`;
                if (Math.abs(n) >= 1000) return `${(n / 1000).toFixed(0)}K`;
                return n;
              },
            },
            border: { display: false },
          },
        },
      },
    });
  }

  function renderFindings(result = {}, assistantContent = "") {
    els.findingsList.innerHTML = "";

    const findings = Array.isArray(result.findings) ? result.findings : [];
    const items = findings.length
      ? findings
      : assistantContent
        ? [{ title: "Grounded conclusion", evidence: assistantContent, significance: "high" }]
        : [];

    if (!items.length) {
      els.findingsList.innerHTML = '<p class="recent-empty">No ranked findings for this turn.</p>';
      return;
    }

    items.slice(0, 6).forEach((finding, index) => {
      const sig = (finding.significance || "medium").toLowerCase();
      const row = document.createElement("div");
      row.className = "finding";
      row.innerHTML = `
        <span class="finding-index">${index + 1}</span>
        <div class="finding-copy">
          <strong>${escapeHtml(finding.title || `Finding ${index + 1}`)}</strong>
          <p>${escapeHtml(finding.evidence || finding.summary || "")}</p>
        </div>
        <span class="significance significance--${escapeHtml(sig)}">${escapeHtml(sig)}</span>
      `;
      els.findingsList.appendChild(row);
    });
  }

  function renderContext(context = {}) {
    const rows = [
      ["Metric", context.metric],
      ["Period", context.primary_period && context.comparison_period
        ? `${context.comparison_period} → ${context.primary_period}`
        : context.primary_period],
      ["Region", context.comparison_regions?.length
        ? context.comparison_regions.join(" vs ")
        : context.region],
      ["Plan", context.comparison_plans?.length
        ? context.comparison_plans.join(" vs ")
        : context.subscription_plan],
      ["Drill-down", context.drilldown_dimension],
      ["Revision", context.revision],
    ].filter(([, value]) => value !== null && value !== undefined && value !== "");

    els.contextGrid.innerHTML = rows.length
      ? rows.map(([label, value]) => `<dt>${escapeHtml(label)}</dt><dd>${escapeHtml(value)}</dd>`).join("")
      : '<dt>Context</dt><dd>New conversation</dd>';
  }

  function normalizeEvidence(execution) {
    const result = execution?.result || {};

    if (Array.isArray(result.evidence)) {
      return result.evidence.map((item, index) => ({
        evidence_id: item.evidence_id || `E${index + 1}`,
        title: item.title || `Evidence ${index + 1}`,
        summary: item.summary || "",
        sql: item.sql || "",
        tables: item.tables || [],
        rows: item.rows || [],
        row_count: item.row_count ?? (item.rows || []).length,
      }));
    }

    const steps = result?.plan?.steps;
    if (Array.isArray(steps)) {
      return steps
        .filter((step) => step.status === "completed")
        .map((step, index) => ({
          evidence_id: `E${index + 1}`,
          title: step.title || `Evidence ${index + 1}`,
          summary: step.evidence_summary || "",
          sql: step.sql || "",
          tables: step.tables || [],
          rows: step.rows || [],
          row_count: step.row_count ?? (step.rows || []).length,
        }));
    }

    if (result.sql || result?.evidence?.rows) {
      return [{
        evidence_id: "E1",
        title: "Query evidence",
        summary: result.answer || "",
        sql: result.sql || "",
        tables: result.selected_tables || [],
        rows: result?.evidence?.rows || [],
        row_count: result?.evidence?.row_count ?? 0,
      }];
    }

    return [];
  }

  function renderEvidence(items = []) {
    els.evidenceGrid.innerHTML = "";

    if (!items.length) {
      els.evidenceGrid.innerHTML = '<p class="recent-empty">No evidence payload for this turn.</p>';
      return;
    }

    items.slice(0, 8).forEach((item) => {
      const card = document.createElement("article");
      card.className = "evidence-card";
      const rowsPreview = JSON.stringify((item.rows || []).slice(0, 8), null, 2);

      card.innerHTML = `
        <div class="evidence-summary">
          <div class="evidence-topline">
            <span class="evidence-id">${escapeHtml(item.evidence_id)}</span>
            <strong title="${escapeHtml(item.title)}">${escapeHtml(item.title)}</strong>
          </div>
          <p>${escapeHtml(item.summary || "Executed database evidence.")}</p>
          <div class="evidence-footer">
            <span>${escapeHtml(item.row_count ?? 0)} row${Number(item.row_count) === 1 ? "" : "s"}</span>
            <button class="evidence-toggle" type="button">View</button>
          </div>
        </div>
        <div class="evidence-details">
          ${item.sql ? `<pre class="code-block">${escapeHtml(item.sql)}</pre>` : ""}
          ${rowsPreview && rowsPreview !== "[]" ? `<pre class="rows-block">${escapeHtml(rowsPreview)}</pre>` : ""}
        </div>
      `;

      card.querySelector(".evidence-toggle").addEventListener("click", (event) => {
        card.classList.toggle("is-open");
        event.currentTarget.textContent = card.classList.contains("is-open") ? "Hide" : "View";
      });

      els.evidenceGrid.appendChild(card);
    });
  }

  function renderSuggestedFollowups(response) {
    const context = response?.context || {};
    const prompts = [];

    if (!context.region && !(context.comparison_regions || []).length) {
      prompts.push("Investigate South.");
    }
    if (context.region) {
      prompts.push(`Compare ${context.region} with North.`);
    } else {
      prompts.push("Compare South with North.");
    }
    prompts.push("Break South down by plan.");
    prompts.push("Explain this result.");
    prompts.push("Are you sure payment failures caused it?");

    els.followupButtons.innerHTML = "";
    prompts.slice(0, 5).forEach((prompt) => {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = prompt.replace(/\.$/, "");
      button.addEventListener("click", () => sendTurn(prompt));
      els.followupButtons.appendChild(button);
    });
    els.suggestedFollowups.hidden = false;
  }

  function humanizeTrustValue(value) {
    if (!value) return "—";
    return String(value)
      .replaceAll("_", " ")
      .replace(/\b\w/g, (letter) => letter.toUpperCase());
  }

  function renderTrust(execution = {}) {
    const confidence = execution.confidence || null;
    const governance = execution.governance || null;
    const provenance = execution.provenance || [];
    const trace = execution.trace || null;

    if (!confidence && !governance && !provenance.length && !trace) {
      els.trustPanel.hidden = true;
      return;
    }

    els.trustPanel.hidden = false;
    els.trustPanel.classList.toggle(
      "governance-blocked",
      governance?.status === "blocked",
    );

    els.trustConfidence.textContent = confidence
      ? humanizeTrustValue(confidence.level)
      : "Stored evidence";

    els.trustCausality.textContent = confidence
      ? humanizeTrustValue(confidence.causality_status)
      : "Not assessed";

    els.trustGovernance.textContent = governance
      ? humanizeTrustValue(governance.status)
      : "Passed";

    els.trustGrounding.textContent = provenance.length
      ? `${provenance.length} source${provenance.length === 1 ? "" : "s"}`
      : "No evidence";

    els.trustRationale.textContent =
      confidence?.rationale ||
      "This reopened investigation contains stored grounded evidence.";

    els.trustCausalityNote.textContent =
      confidence?.causality_note ||
      "No causal assessment was stored for this earlier turn.";

    els.provenanceList.innerHTML = "";
    provenance.forEach((item) => {
      const chip = document.createElement("span");
      chip.className = "provenance-chip";
      const tables = (item.tables || []).join(", ") || "stored evidence";
      const fingerprint = item.sql_fingerprint
        ? ` · ${item.sql_fingerprint}`
        : "";
      chip.innerHTML = `<b>${escapeHtml(item.evidence_id)}</b> ${escapeHtml(tables)}${escapeHtml(fingerprint)}`;
      els.provenanceList.appendChild(chip);
    });

    if (!provenance.length) {
      els.provenanceList.innerHTML =
        '<span class="recent-empty">No provenance items for this turn.</span>';
    }

    if (trace) {
      els.traceBlock.hidden = false;
      els.traceSummary.textContent =
        `${trace.duration_ms} ms total · ${trace.query_count} SQL quer${trace.query_count === 1 ? "y" : "ies"} · ` +
        `${trace.query_time_ms} ms database time · evidence reused: ${trace.evidence_reused ? "yes" : "no"} · ` +
        `trace ${trace.trace_id}`;
    } else {
      els.traceBlock.hidden = true;
      els.traceSummary.textContent = "—";
    }
  }

  function executionStatusLabel(status) {
    if (status === "completed") return "Completed";
    if (status === "blocked") return "Blocked";
    if (status === "no_evidence") return "Needs evidence";
    if (status === "needs_clarification") return "Needs clarification";
    return humanizeTrustValue(status || "Ready");
  }

  function executionAnalysisTitle(execution, result) {
    if (execution.status === "blocked") {
      return "Request blocked by governance";
    }
    if (execution.status === "no_evidence") {
      return "More evidence is required";
    }
    if (execution.status === "needs_clarification") {
      return "Clarification required";
    }
    return (
      result?.plan?.investigation_goal ||
      result?.conclusion ||
      "Grounded analysis"
    );
  }

  function renderAnalysis(response) {
    const execution = response.execution || {};
    const result = execution.result || {};
    const assistantContent = response.assistant_message?.content || "";

    els.analysisPanel.hidden = false;
    els.analysisTitle.textContent =
      executionAnalysisTitle(execution, result);

    els.analysisStatus.textContent =
      executionStatusLabel(execution.status);

    els.analysisStatus.className = "completed-chip";
    if (execution.status === "blocked") {
      els.analysisStatus.classList.add("is-error");
    } else if (execution.status !== "completed") {
      els.analysisStatus.classList.add("is-running");
    }

    renderTrust(execution);
    renderKpis(execution.kpis || []);
    renderChart(execution.charts || []);
    renderFindings(result, assistantContent);
    renderContext(response.context || {});
    renderEvidence(normalizeEvidence(execution));
    renderSuggestedFollowups(response);
  }

  async function deleteInvestigation(session) {
    if (state.busy) return;

    const title = session.title || "Untitled investigation";
    const confirmed = window.confirm(
      `Delete "${title}"?\n\nThis permanently removes the conversation, its evidence, and local trace history.`
    );
    if (!confirmed) return;

    try {
      await api(`/api/v3/sessions/${encodeURIComponent(session.session_id)}`, {
        method: "DELETE",
      });

      const deletedActiveSession = session.session_id === state.sessionId;

      if (deletedActiveSession) {
        resetWorkspace();
      }

      await refreshSessions();

      if (els.investigationsDrawer.classList.contains("is-open")) {
        await refreshInvestigationsDrawer();
      }

      showToast("Investigation deleted.");
    } catch (error) {
      showToast(error.message || "Could not delete the investigation.");
    }
  }

  function closeInvestigationsDrawer() {
    els.investigationsDrawer.classList.remove("is-open");
    els.investigationsDrawer.setAttribute("aria-hidden", "true");
    document.body.style.overflow = "";
  }

  async function openInvestigationsDrawer() {
    els.investigationsDrawer.classList.add("is-open");
    els.investigationsDrawer.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";
    await refreshInvestigationsDrawer();
  }

  async function refreshInvestigationsDrawer() {
    try {
      const sessions = await api("/api/v3/sessions?limit=100");
      els.investigationsDrawerList.innerHTML = "";

      if (!sessions.length) {
        els.investigationsDrawerList.innerHTML =
          '<div class="drawer-empty">No investigations yet. Start a new investigation to create one.</div>';
        return;
      }

      sessions.forEach((session) => {
        const turns = (session.messages || []).filter((message) => message.role === "user").length;

        const row = document.createElement("div");
        row.className = `drawer-investigation-row${session.session_id === state.sessionId ? " is-active" : ""}`;

        const openButton = document.createElement("button");
        openButton.type = "button";
        openButton.className = "drawer-investigation";
        openButton.innerHTML = `
          <span class="drawer-investigation__copy">
            <strong>${escapeHtml(session.title || "Untitled investigation")}</strong>
            <span>${escapeHtml(formatRelative(session.updated_at))} · ${turns} turn${turns === 1 ? "" : "s"}</span>
          </span>
          <span class="drawer-investigation__meta">Open →</span>
        `;
        openButton.addEventListener("click", async () => {
          closeInvestigationsDrawer();
          await loadSession(session.session_id);
        });

        const deleteButton = document.createElement("button");
        deleteButton.type = "button";
        deleteButton.className = "drawer-delete";
        deleteButton.title = "Delete investigation";
        deleteButton.setAttribute("aria-label", `Delete ${session.title || "investigation"}`);
        deleteButton.textContent = "Delete";
        deleteButton.addEventListener("click", () => deleteInvestigation(session));

        row.append(openButton, deleteButton);
        els.investigationsDrawerList.appendChild(row);
      });
    } catch (error) {
      els.investigationsDrawerList.innerHTML =
        '<div class="drawer-empty">Could not load investigations.</div>';
    }
  }

  async function refreshSessions() {
    try {
      const sessions = await api("/api/v3/sessions?limit=12");
      els.recentList.innerHTML = "";

      if (!sessions.length) {
        els.recentList.innerHTML = '<div class="recent-empty">No investigations yet.</div>';
        return;
      }

      sessions.forEach((session) => {
        const row = document.createElement("div");
        row.className = `recent-row${session.session_id === state.sessionId ? " is-active" : ""}`;

        const openButton = document.createElement("button");
        openButton.type = "button";
        openButton.className = "recent-item";
        openButton.dataset.sessionId = session.session_id;
        openButton.innerHTML = `
          <strong>${escapeHtml(session.title || "Untitled investigation")}</strong>
          <span>${escapeHtml(formatRelative(session.updated_at))}</span>
        `;
        openButton.addEventListener("click", () => loadSession(session.session_id));

        const deleteButton = document.createElement("button");
        deleteButton.type = "button";
        deleteButton.className = "recent-delete";
        deleteButton.title = "Delete investigation";
        deleteButton.setAttribute("aria-label", `Delete ${session.title || "investigation"}`);
        deleteButton.textContent = "×";
        deleteButton.addEventListener("click", () => deleteInvestigation(session));

        row.append(openButton, deleteButton);
        els.recentList.appendChild(row);
      });
    } catch (error) {
      els.recentList.innerHTML = '<div class="recent-empty">Could not load sessions.</div>';
    }
  }

  async function loadSession(sessionId) {
    if (state.busy) return;

    try {
      setBusy(true, "Opening investigation", "Loading conversation and evidence from this runtime…");

      const [session, evidence] = await Promise.all([
        api(`/api/v3/sessions/${encodeURIComponent(sessionId)}`),
        api(`/api/v3/sessions/${encodeURIComponent(sessionId)}/evidence`),
      ]);

      state.sessionId = sessionId;
      state.session = session;
      state.latestResponse = null;
      clearChart();

      els.emptyState.hidden = true;
      els.conversationFeed.innerHTML = "";
      els.analysisPanel.hidden = true;
      els.trustPanel.hidden = true;
      els.trustDetails.hidden = true;

      (session.messages || []).forEach((message) => {
        appendTurn(message.role, message.content, message.created_at);
      });

      updateDetails(session, "Active");
      renderContext(session.context || {});

      if (evidence.length) {
        const snapshot = evidence[evidence.length - 1];
        els.analysisPanel.hidden = false;
        els.analysisTitle.textContent = snapshot.conclusion || "Stored evidence";
        renderTrust({
          confidence: snapshot.confidence || null,
          governance: snapshot.governance || null,
          provenance: snapshot.provenance || [],
          trace: null,
        });
        renderKpis([]);
        renderChart([]);
        renderFindings({}, snapshot.conclusion || "");
        renderEvidence(snapshot.evidence || []);
        renderSuggestedFollowups({ context: session.context || {} });
      }

      await refreshSessions();
    } catch (error) {
      showToast(error.message);
    } finally {
      setBusy(false);
    }
  }

  async function sendTurn(rawMessage) {
    const message = String(rawMessage || "").trim();
    if (!message || state.busy) return;

    try {
      const sessionId = await ensureSession();

      appendTurn("user", message, new Date().toISOString());
      els.composerInput.value = "";
      els.globalSearchInput.value = "";
      autosizeComposer();

      setBusy(true);
      if (state.session) updateDetails(state.session, "Running");

      const response = await api(`/api/v3/sessions/${encodeURIComponent(sessionId)}/turns`, {
        method: "POST",
        body: JSON.stringify({ message }),
      });

      state.latestResponse = response;

      appendTurn(
        "assistant",
        response.assistant_message?.content || "The request completed.",
        response.assistant_message?.created_at || new Date().toISOString(),
      );

      renderAnalysis(response);

      state.session = await api(`/api/v3/sessions/${encodeURIComponent(sessionId)}`);
      updateDetails(
        state.session,
        executionStatusLabel(response.execution?.status),
      );
      await refreshSessions();
    } catch (error) {
      appendTurn(
        "assistant",
        `I couldn't complete that request: ${error.message}`,
        new Date().toISOString(),
      );
      if (state.session) updateDetails(state.session, "Error");
      showToast(error.message);
    } finally {
      setBusy(false);
    }
  }

  function autosizeComposer() {
    const input = els.composerInput;
    input.style.height = "auto";
    input.style.height = `${Math.min(input.scrollHeight, 140)}px`;
  }

  els.trustToggle.addEventListener("click", () => {
    const opening = els.trustDetails.hidden;
    els.trustDetails.hidden = !opening;
    els.trustToggle.textContent = opening ? "Hide details" : "Details";
  });

  function wirePromptButtons() {
    document.querySelectorAll("[data-prompt]").forEach((button) => {
      button.addEventListener("click", () => {
        const prompt = button.dataset.prompt || "";
        if (prompt) sendTurn(prompt);
      });
    });
  }

  els.composerForm.addEventListener("submit", (event) => {
    event.preventDefault();
    sendTurn(els.composerInput.value);
  });

  els.composerInput.addEventListener("input", autosizeComposer);
  els.composerInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      els.composerForm.requestSubmit();
    }
  });

  els.globalSearchForm.addEventListener("submit", (event) => {
    event.preventDefault();
    sendTurn(els.globalSearchInput.value);
  });

  els.newButton.addEventListener("click", resetWorkspace);
  els.railNewButton.addEventListener("click", resetWorkspace);
  els.refreshSessionsButton.addEventListener("click", refreshSessions);

  els.investigationsNav.addEventListener("click", openInvestigationsDrawer);

  els.closeInvestigationsButton.addEventListener("click", closeInvestigationsDrawer);
  els.investigationsBackdrop.addEventListener("click", closeInvestigationsDrawer);

  els.drawerRefreshInvestigationsButton.addEventListener("click", refreshInvestigationsDrawer);

  els.drawerNewInvestigationButton.addEventListener("click", () => {
    closeInvestigationsDrawer();
    resetWorkspace();
  });

  const scrollToEvidence = () => {
    if (els.analysisPanel.hidden) {
      showToast("Run an investigation first.");
      return;
    }
    els.evidenceSection.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  els.evidenceNav.addEventListener("click", scrollToEvidence);
  els.railEvidenceButton.addEventListener("click", scrollToEvidence);

  els.viewAllEvidenceButton.addEventListener("click", () => {
    const cards = [...els.evidenceGrid.querySelectorAll(".evidence-card")];
    const shouldOpen = cards.some((card) => !card.classList.contains("is-open"));
    cards.forEach((card) => {
      card.classList.toggle("is-open", shouldOpen);
      const button = card.querySelector(".evidence-toggle");
      if (button) button.textContent = shouldOpen ? "Hide" : "View";
    });
    els.viewAllEvidenceButton.textContent = shouldOpen ? "Collapse all" : "Expand all";
  });

  els.copyResponseButton.addEventListener("click", async () => {
    const text = state.latestResponse?.assistant_message?.content;
    if (!text) {
      showToast("No response to copy yet.");
      return;
    }

    try {
      await navigator.clipboard.writeText(text);
      showToast("Latest response copied.");
    } catch {
      showToast("Clipboard access is unavailable.");
    }
  });

  els.mobileMenuButton.addEventListener("click", () => {
    els.sidebar.classList.toggle("is-open");
  });

  document.addEventListener("click", (event) => {
    if (window.innerWidth > 820) return;
    if (
      els.sidebar.classList.contains("is-open") &&
      !els.sidebar.contains(event.target) &&
      event.target !== els.mobileMenuButton
    ) {
      els.sidebar.classList.remove("is-open");
    }
  });

  wirePromptButtons();
  refreshSessions();
  autosizeComposer();
})();
