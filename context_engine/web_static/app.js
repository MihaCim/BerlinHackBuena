const state = {
  busy: false,
};

const $ = (id) => document.getElementById(id);

const controls = [
  "bootstrapBtn",
  "deltaBtn",
  "replayBtn",
  "refreshBtn",
  "loadContextBtn",
];

function useAi() {
  return $("useAi").checked;
}

function setBusy(value, label = "") {
  state.busy = value;
  document.body.classList.toggle("busy", value);
  for (const id of controls) {
    $(id).disabled = value;
  }
  if (label) {
    log(label);
  }
}

function log(message, payload = null) {
  const stamp = new Date().toLocaleTimeString();
  const extra = payload ? `\n${JSON.stringify(payload, null, 2)}` : "";
  $("runLog").textContent = `[${stamp}] ${message}${extra}`;
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const text = await response.text();
  if (!response.ok) {
    throw new Error(text || response.statusText);
  }
  const contentType = response.headers.get("content-type") || "";
  return contentType.includes("application/json") ? JSON.parse(text) : text;
}

async function refreshStatus() {
  const status = await api("/api/status");
  renderStatus(status);
  return status;
}

function renderStatus(status) {
  $("watermark").textContent = `watermark: ${status.watermark}`;
  $("langgraph").textContent = status.context_exists ? "context ready" : "context missing";
  $("patchCount").textContent = `patches: ${status.patch_count}`;

  const metrics = status.metrics || {};
  const entries = [
    ["bank tx", metrics.bank_transactions],
    ["invoices", metrics.invoices],
    ["emails", metrics.emails],
    ["letters", metrics.letters],
    ["topics", metrics.topics],
    ["anomalies", metrics.anomalies],
  ];
  $("metricsGrid").innerHTML = entries
    .map(([label, value]) => `<div class="metric"><span>${label}</span><strong>${value ?? "-"}</strong></div>`)
    .join("");
}

function renderRun(result) {
  renderStatus({
    watermark: result.watermark,
    metrics: result.metrics,
    context_exists: true,
    patch_count: "-",
  });
  const summary = {
    watermark: result.watermark,
    patches: result.patches,
    human_notes_preserved: result.human_notes_preserved,
    langgraph_available: result.langgraph_available,
    agentic_note: result.agentic_note || "",
  };
  log("Run completed", summary);
}

async function runBootstrap() {
  setBusy(true, "Bootstrapping context...");
  try {
    const result = await api("/api/bootstrap", {
      method: "POST",
      body: JSON.stringify({ use_ai: useAi() }),
    });
    renderRun(result);
    await loadContext();
  } catch (error) {
    log("Bootstrap failed", { error: error.message });
  } finally {
    setBusy(false);
    await refreshStatus();
  }
}

async function runDelta() {
  const day = $("daySelect").value;
  setBusy(true, `Applying ${day}...`);
  try {
    const result = await api("/api/apply-delta", {
      method: "POST",
      body: JSON.stringify({ day, use_ai: useAi() }),
    });
    renderRun(result);
    await loadContext();
  } catch (error) {
    log("Delta failed", { error: error.message });
  } finally {
    setBusy(false);
    await refreshStatus();
  }
}

async function runReplay() {
  setBusy(true, "Replaying all deltas...");
  try {
    const result = await api("/api/replay", {
      method: "POST",
      body: JSON.stringify({ use_ai: useAi() }),
    });
    renderRun(result);
    await loadContext();
  } catch (error) {
    log("Replay failed", { error: error.message });
  } finally {
    setBusy(false);
    await refreshStatus();
  }
}

async function loadContext() {
  try {
    $("contextPreview").textContent = await api("/api/context");
  } catch (error) {
    $("contextPreview").textContent = error.message;
  }
}

async function askQuestion(event) {
  event.preventDefault();
  const question = $("questionInput").value.trim();
  if (!question) {
    return;
  }
  $("answerBox").textContent = "Thinking...";
  try {
    const result = await api("/api/ask", {
      method: "POST",
      body: JSON.stringify({ question, use_ai: useAi() }),
    });
    $("answerBox").textContent = result.answer;
  } catch (error) {
    $("answerBox").textContent = error.message;
  }
}

$("bootstrapBtn").addEventListener("click", runBootstrap);
$("deltaBtn").addEventListener("click", runDelta);
$("replayBtn").addEventListener("click", runReplay);
$("refreshBtn").addEventListener("click", async () => {
  const status = await refreshStatus();
  log("Status refreshed", status);
});
$("loadContextBtn").addEventListener("click", loadContext);
$("askForm").addEventListener("submit", askQuestion);
document.querySelectorAll("[data-question]").forEach((button) => {
  button.addEventListener("click", () => {
    $("questionInput").value = button.dataset.question;
    $("askForm").requestSubmit();
  });
});

refreshStatus()
  .then(loadContext)
  .catch((error) => log("Initial load failed", { error: error.message }));
