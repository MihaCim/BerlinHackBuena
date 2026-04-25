const state = {
  busy: false,
  view: "context",
  latestPatch: null,
  contextText: "",
  resources: [],
  editingContext: false,
};

const $ = (id) => document.getElementById(id);

const controls = [
  "bootstrapBtn",
  "deltaBtn",
  "replayBtn",
  "refreshBtn",
  "loadContextBtn",
  "processIntakeBtn",
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

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
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
  await loadPatches();
  await loadResources();
  return status;
}

function renderStatus(status) {
  $("watermark").textContent = status.watermark;
  $("contextState").textContent = status.context_exists ? "ready" : "missing";
  $("patchCount").textContent = String(status.patch_count);
  $("userEditCount").textContent = String(status.user_edits ?? 0);
  $("intakeCount").textContent = String(status.staged_resources ?? 0);
  $("langgraph").textContent = status.ai_configured ? `${status.ai_provider || "AI"} ready` : "deterministic mode";
  $("latestPatch").textContent = status.status_note || `latest patch: ${status.latest_patch || "none"}`;

  const metrics = status.metrics || {};
  const entries = [
    ["invoices", metrics.invoices],
    ["topics", metrics.topics],
    ["anomalies", metrics.anomalies],
    ["patches", status.patch_count],
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
    latest_patch: result.watermark ? `${result.watermark}.patch.json` : null,
  });
  log("Run completed", {
    watermark: result.watermark,
    patches: result.patches,
    human_notes_preserved: result.human_notes_preserved,
    langgraph_available: result.langgraph_available,
    agentic_note: result.agentic_note || "",
  });
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
    state.contextText = await api("/api/context");
    renderPreview();
  } catch (error) {
    state.contextText = error.message;
    renderPreview();
  }
}

async function loadPatches() {
  try {
    const result = await api("/api/patches");
    state.latestPatch = result.latest;
    renderPatchList(result.patches || []);
    renderPreview();
  } catch (error) {
    $("patchList").innerHTML = `<div class="patch-item"><span>patches unavailable</span><strong>${error.message}</strong></div>`;
  }
}

function renderPatchList(patches) {
  if (!patches.length) {
    $("patchList").innerHTML = `<div class="patch-item"><span>No patches yet</span><strong>run bootstrap</strong></div>`;
    return;
  }
  $("patchList").innerHTML = patches
    .slice(-6)
    .reverse()
    .map((patch) => `<div class="patch-item"><span>${patch.name}</span><strong>${patch.size} B</strong></div>`)
    .join("");
}

function renderPreview() {
  renderContextEditMode();
  if (state.view === "patch") {
    $("contextPreview").textContent = state.latestPatch
      ? JSON.stringify(state.latestPatch, null, 2)
      : "No patch log loaded yet.";
  } else {
    $("contextPreview").textContent = state.contextText || "The compiled markdown will appear here.";
  }
}

function renderContextEditMode() {
  const isContext = state.view === "context";
  $("editContextBtn").hidden = !isContext || state.editingContext;
  $("saveContextBtn").hidden = !isContext || !state.editingContext;
  $("cancelContextBtn").hidden = !isContext || !state.editingContext;
  $("contextPreview").hidden = isContext && state.editingContext;
  $("contextEditor").hidden = !isContext || !state.editingContext;
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

function startContextEdit() {
  if (state.view !== "context") {
    state.view = "context";
    document.querySelectorAll("[data-view]").forEach((tab) => tab.classList.remove("active"));
    document.querySelector('[data-view="context"]').classList.add("active");
  }
  state.editingContext = true;
  $("contextEditor").value = state.contextText || "";
  $("contextEditStatus").textContent = "Editing context.md directly. Your changed lines will be saved inside protected <user> tags.";
  renderPreview();
  $("contextEditor").focus();
}

function cancelContextEdit() {
  state.editingContext = false;
  $("contextEditor").value = "";
  $("contextEditStatus").textContent = "Edit the artifact here when a human knows the correct context. Saved changes are wrapped in protected <user> tags.";
  renderPreview();
}

async function saveContextEdit() {
  const content = $("contextEditor").value;
  if (!content.trim()) {
    $("contextEditStatus").textContent = "Context cannot be empty.";
    return;
  }
  $("contextEditStatus").textContent = "Saving artifact edit with protected <user> tags...";
  try {
    const result = await api("/api/context", {
      method: "PUT",
      body: JSON.stringify({ content, author: "frontend-user" }),
    });
    state.contextText = result.content;
    state.editingContext = false;
    $("contextEditor").value = "";
    $("contextEditStatus").textContent = result.message;
    renderPreview();
    await refreshStatus();
  } catch (error) {
    $("contextEditStatus").textContent = error.message;
  }
}

async function stageResource(event) {
  event.preventDefault();
  const name = $("resourceName").value.trim();
  const kind = $("resourceType").value;
  const content = $("resourceContent").value.trim();
  const notes = $("resourceNotes").value.trim();
  if (!content) {
    $("resourceStatus").textContent = "Paste content or choose a readable text file first.";
    return;
  }
  $("resourceStatus").textContent = "Staging resource...";
  try {
    const result = await api("/api/resources", {
      method: "POST",
      body: JSON.stringify({
        name: name || `${kind}-resource.txt`,
        kind,
        content,
        notes,
      }),
    });
    $("resourceStatus").textContent = `${result.resource.name} is staged for ingestion.`;
    $("resourceContent").value = "";
    $("resourceNotes").value = "";
    await loadResources();
  } catch (error) {
    $("resourceStatus").textContent = error.message;
  }
}

async function processIntake() {
  $("resourceStatus").textContent = "Agent is validating staged resources against schemas...";
  try {
    const result = await api("/api/process-intake", {
      method: "POST",
      body: JSON.stringify({ use_ai: useAi() }),
    });
    const processed = result.processed || [];
    const written = processed.filter((item) => item.status === "written_to_context").length;
    const rejected = processed.filter((item) => item.status === "rejected").length;
    $("resourceStatus").textContent = `Agent processed ${processed.length} resource(s): ${written} written, ${rejected} rejected.`;
    log("Agentic intake completed", result);
    await loadResources();
    await loadContext();
    await refreshStatus();
  } catch (error) {
    $("resourceStatus").textContent = error.message;
    log("Agentic intake failed", { error: error.message });
  }
}

async function loadResources() {
  try {
    const result = await api("/api/resources");
    state.resources = result.resources || [];
    renderResources();
  } catch (error) {
    $("resourceList").innerHTML = `<div class="resource-item"><span>resources unavailable</span><strong>${escapeHtml(error.message)}</strong></div>`;
  }
}

function renderResources() {
  if (!state.resources.length) {
    $("resourceList").innerHTML = `<div class="resource-item"><span>No staged resources yet</span><strong>ready</strong></div>`;
    return;
  }
  $("resourceList").innerHTML = state.resources
    .slice(0, 4)
    .map(
      (resource) => `
        <div class="resource-item">
          <span>${escapeHtml(resource.name)}</span>
          <strong>${escapeHtml(resource.kind)} / ${escapeHtml(resource.status || "staged")}</strong>
        </div>
      `,
    )
    .join("");
}

async function readResourceFile(event) {
  const [file] = event.target.files;
  if (!file) {
    return;
  }
  $("resourceName").value = $("resourceName").value || file.name;
  try {
    $("resourceContent").value = await file.text();
    $("resourceStatus").textContent = `${file.name} loaded locally. Review, then stage it.`;
  } catch (error) {
    $("resourceStatus").textContent = `Could not read ${file.name}. Paste extracted text instead.`;
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
$("resourceForm").addEventListener("submit", stageResource);
$("resourceFile").addEventListener("change", readResourceFile);
$("processIntakeBtn").addEventListener("click", processIntake);
$("editContextBtn").addEventListener("click", startContextEdit);
$("saveContextBtn").addEventListener("click", saveContextEdit);
$("cancelContextBtn").addEventListener("click", cancelContextEdit);

document.querySelectorAll("[data-question]").forEach((button) => {
  button.addEventListener("click", () => {
    $("questionInput").value = button.dataset.question;
    $("askForm").requestSubmit();
  });
});

document.querySelectorAll("[data-view]").forEach((button) => {
  button.addEventListener("click", () => {
    state.view = button.dataset.view;
    state.editingContext = false;
    document.querySelectorAll("[data-view]").forEach((tab) => tab.classList.remove("active"));
    button.classList.add("active");
    renderPreview();
  });
});

refreshStatus()
  .then(loadContext)
  .catch((error) => log("Initial load failed", { error: error.message }));
