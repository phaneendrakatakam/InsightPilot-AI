(() => {
  "use strict";

  const askForm = document.getElementById("askForm");
  const questionInput = document.getElementById("questionInput");
  const askButton = document.getElementById("askButton");
  const charCounter = document.getElementById("charCounter");
  const workspace = document.getElementById("workspace");
  const workspaceQuestion = document.getElementById("workspaceQuestion");
  const newQuestionButton = document.getElementById("newQuestionButton");
  const thinkingPanel = document.getElementById("thinkingPanel");
  const thinkingTitle = document.getElementById("thinkingTitle");
  const thinkingDetail = document.getElementById("thinkingDetail");
  const responseStack = document.getElementById("responseStack");
  const answerText = document.getElementById("answerText");
  const observationList = document.getElementById("observationList");
  const interpretationText = document.getElementById("interpretationText");
  const caveatBox = document.getElementById("caveatBox");
  const evidenceMeta = document.getElementById("evidenceMeta");
  const schemaPills = document.getElementById("schemaPills");
  const evidenceTable = document.getElementById("evidenceTable");
  const emptyEvidence = document.getElementById("emptyEvidence");
  const sqlToggle = document.getElementById("sqlToggle");
  const sqlCode = document.getElementById("sqlCode");
  const copySqlButton = document.getElementById("copySqlButton");
  const clarificationState = document.getElementById("clarificationState");
  const clarificationMessage = document.getElementById("clarificationMessage");
  const errorState = document.getElementById("errorState");
  const errorMessage = document.getElementById("errorMessage");
  const toast = document.getElementById("toast");
  const suggestionCards = [...document.querySelectorAll(".suggestion-card")];

  let isBusy = false;
  let thinkingTimer = null;

  const thinkingSteps = [
    ["Understanding your question", "Reading the business intent and requested metric..."],
    ["Selecting relevant schema", "Keeping only the tables needed for this question..."],
    ["Generating safe SQL", "Preparing a read-only PostgreSQL query..."],
    ["Validating query", "Checking table access, safety rules, and result limits..."],
    ["Investigating live data", "Executing against the read-only enterprise dataset..."],
    ["Grounding the answer", "Explaining only what the returned evidence supports..."],
  ];

  function autoResizeTextarea() {
    questionInput.style.height = "auto";
    questionInput.style.height = `${Math.min(questionInput.scrollHeight, 145)}px`;
    charCounter.textContent = `${questionInput.value.length} / 500`;
  }

  function showToast(message) {
    toast.textContent = message;
    toast.classList.add("is-visible");
    window.clearTimeout(showToast.timer);
    showToast.timer = window.setTimeout(() => toast.classList.remove("is-visible"), 1800);
  }

  function resetStates() {
    responseStack.hidden = true;
    clarificationState.hidden = true;
    errorState.hidden = true;
    thinkingPanel.hidden = true;
  }

  function showWorkspace(question) {
    document.body.classList.add("has-result");
    workspace.setAttribute("aria-hidden", "false");
    workspace.classList.add("is-visible");
    workspaceQuestion.textContent = question;
    window.setTimeout(() => workspace.scrollIntoView({ behavior: "smooth", block: "start" }), 160);
  }

  function startThinking() {
    let index = 0;
    thinkingPanel.hidden = false;
    thinkingTitle.textContent = thinkingSteps[0][0];
    thinkingDetail.textContent = thinkingSteps[0][1];

    thinkingTimer = window.setInterval(() => {
      index = (index + 1) % thinkingSteps.length;
      [thinkingTitle, thinkingDetail].forEach((el) => {
        el.animate(
          [{ opacity: 0, transform: "translateY(4px)" }, { opacity: 1, transform: "translateY(0)" }],
          { duration: 300, easing: "ease-out" }
        );
      });
      thinkingTitle.textContent = thinkingSteps[index][0];
      thinkingDetail.textContent = thinkingSteps[index][1];
    }, 1100);
  }

  function stopThinking() {
    window.clearInterval(thinkingTimer);
    thinkingTimer = null;
    thinkingPanel.hidden = true;
  }

  function setBusy(value) {
    isBusy = value;
    askButton.disabled = value;
    askButton.classList.toggle("is-loading", value);
    questionInput.disabled = value;
  }

  function renderSchemaPills(tables = []) {
    schemaPills.innerHTML = "";
    tables.forEach((table) => {
      const pill = document.createElement("span");
      pill.className = "schema-pill";
      pill.textContent = table;
      schemaPills.appendChild(pill);
    });
  }

  function renderEvidence(evidence = {}) {
    const thead = evidenceTable.querySelector("thead");
    const tbody = evidenceTable.querySelector("tbody");

    thead.innerHTML = "";
    tbody.innerHTML = "";

    const columns = evidence.columns || [];
    const rows = evidence.rows || [];
    const rowCount = evidence.row_count ?? rows.length;
    const executionMs = evidence.execution_time_ms;
    const pageSize = 25;
    let currentPage = 1;

    const msText =
      typeof executionMs === "number" ? ` · ${executionMs.toFixed(2)} ms` : "";
    evidenceMeta.textContent =
      `${rowCount} row${rowCount === 1 ? "" : "s"}${msText}`;

    let pagination = document.getElementById("evidencePagination");

    if (!pagination) {
      pagination = document.createElement("div");
      pagination.id = "evidencePagination";
      pagination.className = "evidence-pagination";
      evidenceTable.insertAdjacentElement("afterend", pagination);
    }

    if (!rows.length) {
      evidenceTable.hidden = true;
      pagination.hidden = true;
      emptyEvidence.hidden = false;
      return;
    }

    evidenceTable.hidden = false;
    emptyEvidence.hidden = true;

    const headerRow = document.createElement("tr");
    columns.forEach((column) => {
      const th = document.createElement("th");
      th.textContent = column.replaceAll("_", " ");
      headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);

    const totalPages = Math.max(1, Math.ceil(rows.length / pageSize));

    function renderPage() {
      tbody.innerHTML = "";

      const startIndex = (currentPage - 1) * pageSize;
      const endIndex = Math.min(startIndex + pageSize, rows.length);

      rows.slice(startIndex, endIndex).forEach((row, index) => {
        const tr = document.createElement("tr");
        tr.style.animationDelay = `${Math.min(index * 22, 260)}ms`;

        columns.forEach((column) => {
          const td = document.createElement("td");
          const value = row[column];
          td.textContent =
            value === null || value === undefined ? "—" : String(value);
          tr.appendChild(td);
        });

        tbody.appendChild(tr);
      });

      pagination.hidden = rows.length <= pageSize;

      if (rows.length > pageSize) {
        pagination.innerHTML = `
          <div class="evidence-pagination__info">
            <span>Showing</span>
            <strong>${startIndex + 1}–${endIndex}</strong>
            <span>of</span>
            <strong>${rows.length}</strong>
            <span>returned rows</span>
          </div>
          <div class="evidence-pagination__actions">
            <button class="evidence-page-btn" id="evidencePrev" type="button"
              ${currentPage === 1 ? "disabled" : ""}>← Previous</button>
            <span class="evidence-pagination__page">
              Page ${currentPage} of ${totalPages}
            </span>
            <button class="evidence-page-btn" id="evidenceNext" type="button"
              ${currentPage === totalPages ? "disabled" : ""}>Next →</button>
          </div>
        `;

        const prev = document.getElementById("evidencePrev");
        const next = document.getElementById("evidenceNext");

        prev?.addEventListener("click", () => {
          if (currentPage > 1) {
            currentPage -= 1;
            renderPage();
            evidenceTable.scrollIntoView({ behavior: "smooth", block: "start" });
          }
        });

        next?.addEventListener("click", () => {
          if (currentPage < totalPages) {
            currentPage += 1;
            renderPage();
            evidenceTable.scrollIntoView({ behavior: "smooth", block: "start" });
          }
        });
      }
    }

    renderPage();
  }

  function renderAnswered(payload) {
    answerText.textContent = payload.answer || "The query completed successfully.";
    observationList.innerHTML = "";

    const observations = payload.observations || [];
    (observations.length ? observations : ["No additional observations were required."]).forEach((item) => {
      const li = document.createElement("li");
      li.textContent = item;
      observationList.appendChild(li);
    });

    interpretationText.textContent =
      payload.interpretation || "No additional interpretation was required.";

    if (payload.caveat) {
      caveatBox.textContent = payload.caveat;
      caveatBox.hidden = false;
    } else {
      caveatBox.hidden = true;
      caveatBox.textContent = "";
    }

    renderSchemaPills(payload.selected_tables || []);
    renderEvidence(payload.evidence || {});
    applyEvidencePagination(25);
    sqlCode.textContent = payload.sql || "No SQL was returned.";

    document.querySelectorAll(".response-animate").forEach((card) => {
      card.style.animation = "none";
      card.offsetHeight;
      card.style.animation = "";
    });

    responseStack.hidden = false;
  }

  function renderClarification(payload) {
    clarificationMessage.textContent =
      payload.message || payload.detail ||
      "This request needs clarification before InsightPilot can investigate it safely.";
    clarificationState.hidden = false;
  }

  function renderError(message) {
    errorMessage.textContent = message || "The investigation could not be completed.";
    errorState.hidden = false;
  }


  function isScopeRejection(response, payload) {
    return (
      response.status === 422 &&
      typeof payload?.detail === "string" &&
      payload.detail.toLowerCase().includes("approved v1 business schema")
    );
  }

  function applyEvidencePagination(pageSize = 25) {
    const tbody = evidenceTable?.querySelector("tbody");
    const tableShell = evidenceTable?.closest(".table-shell");

    if (!tbody || !tableShell) return;

    const rows = [...tbody.querySelectorAll("tr")];

    const existing = tableShell.querySelector(".qa-pagination");
    if (existing) existing.remove();

    if (rows.length <= pageSize) {
      rows.forEach((row) => {
        row.hidden = false;
      });
      return;
    }

    let currentPage = 1;
    const totalPages = Math.ceil(rows.length / pageSize);

    const pager = document.createElement("div");
    pager.className = "qa-pagination";
    evidenceTable.insertAdjacentElement("afterend", pager);

    function renderPage() {
      const start = (currentPage - 1) * pageSize;
      const end = Math.min(start + pageSize, rows.length);

      rows.forEach((row, index) => {
        row.hidden = index < start || index >= end;
      });

      pager.innerHTML = `
        <div class="qa-pagination__info">
          <span>Showing</span>
          <strong>${start + 1}-${end}</strong>
          <span>of</span>
          <strong>${rows.length}</strong>
          <span>returned rows</span>
        </div>
        <div class="qa-pagination__actions">
          <button class="qa-pagination__btn" id="qaPrev" type="button"
            ${currentPage === 1 ? "disabled" : ""}>Previous</button>
          <span class="qa-pagination__label">
            Page ${currentPage} of ${totalPages}
          </span>
          <button class="qa-pagination__btn" id="qaNext" type="button"
            ${currentPage === totalPages ? "disabled" : ""}>Next</button>
        </div>
      `;

      pager.querySelector("#qaPrev")?.addEventListener("click", () => {
        if (currentPage > 1) {
          currentPage -= 1;
          renderPage();
          evidenceTable.scrollIntoView({ behavior: "smooth", block: "start" });
        }
      });

      pager.querySelector("#qaNext")?.addEventListener("click", () => {
        if (currentPage < totalPages) {
          currentPage += 1;
          renderPage();
          evidenceTable.scrollIntoView({ behavior: "smooth", block: "start" });
        }
      });
    }

    renderPage();
  }


  async function submitQuestion(question) {
    const cleanQuestion = (question || "").trim();
    if (!cleanQuestion || isBusy) return;

    questionInput.value = cleanQuestion;
    autoResizeTextarea();
    resetStates();
    showWorkspace(cleanQuestion);
    setBusy(true);
    startThinking();

    try {
      const response = await fetch("/api/v1/ask", {
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
            : "InsightPilot could not process this request.";

        if (isScopeRejection(response, payload)) {
          renderClarification({ message: detail });
        } else {
          renderError(detail);
        }
        return;
      }

      if (payload?.status === "answered") {
        renderAnswered(payload);
      } else if (payload?.status === "needs_clarification") {
        renderClarification(payload);
      } else {
        renderError("InsightPilot returned an unexpected response state.");
      }
    } catch (error) {
      stopThinking();
      renderError("The UI could not reach the InsightPilot API. Confirm that FastAPI is running.");
      console.error(error);
    } finally {
      setBusy(false);
    }
  }

  askForm.addEventListener("submit", (event) => {
    event.preventDefault();
    submitQuestion(questionInput.value);
  });

  questionInput.addEventListener("input", autoResizeTextarea);
  questionInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      askForm.requestSubmit();
    }
  });

  suggestionCards.forEach((card) => {
    card.addEventListener("click", () => {
      const question = card.dataset.question || "";
      card.animate(
        [
          { transform: "translateY(-5px) scale(1)" },
          { transform: "translateY(-2px) scale(.97)" },
          { transform: "translateY(-5px) scale(1)" },
        ],
        { duration: 260, easing: "ease-out" }
      );
      window.setTimeout(() => submitQuestion(question), 90);
    });
  });

  newQuestionButton.addEventListener("click", () => {
    document.body.classList.remove("has-result");
    workspace.classList.remove("is-visible");
    workspace.setAttribute("aria-hidden", "true");
    resetStates();
    questionInput.value = "";
    autoResizeTextarea();
    window.scrollTo({ top: 0, behavior: "smooth" });
    window.setTimeout(() => questionInput.focus(), 420);
  });

  sqlToggle.addEventListener("click", () => {
    const expanded = sqlToggle.getAttribute("aria-expanded") === "true";
    sqlToggle.setAttribute("aria-expanded", String(!expanded));
  });

  copySqlButton.addEventListener("click", async () => {
    const sql = sqlCode.textContent.trim();
    if (!sql) return;

    try {
      await navigator.clipboard.writeText(sql);
      showToast("SQL copied");
    } catch (_) {
      showToast("Could not copy SQL");
    }
  });

  autoResizeTextarea();
})();
