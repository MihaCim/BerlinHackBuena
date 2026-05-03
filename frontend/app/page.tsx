"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import type { ButtonHTMLAttributes, ReactElement } from "react";

type Theme = "dark" | "light";
type ArtifactView = "context" | "patch";
type Role = "user" | "assistant";
type PendingAction = "intake" | "rollback";
type IconName =
  | "resource"
  | "mechanism"
  | "theme"
  | "threads"
  | "newThread"
  | "trace"
  | "context"
  | "patch"
  | "edit"
  | "save"
  | "cancel"
  | "latest"
  | "rollback"
  | "send"
  | "preview"
  | "apply"
  | "close";

type ChatMessage = {
  id: string;
  role: Role;
  content: string;
  createdAt: string;
};

type ChatThread = {
  id: string;
  title: string;
  createdAt: string;
  messages: ChatMessage[];
};

type PatchFile = {
  name: string;
  size: number;
};

type ResourceRecord = {
  id?: string;
  name: string;
  kind: string;
  notes?: string;
  created_at?: string;
  status?: string;
};

type AskResponse = {
  answer: string;
  building_id?: string;
  routed?: boolean;
  citations?: AgentCitation[];
  trace?: AgentTrace;
  plan?: {
    agent?: string;
    intent?: string;
    mode?: string;
    actor_role?: string;
  };
  agent?: {
    mode?: string;
    intent?: string;
    evidence_titles?: string[];
  };
};

type AgentCitation = {
  rank: number;
  building_id?: string;
  title: string;
  quote: string;
};

type AgentTraceNode = {
  id: string;
  label: string;
  status: "ok" | "blocked" | "error" | "info";
  detail: string;
  tool?: string | null;
};

type AgentTrace = {
  nodes: AgentTraceNode[];
};

type IntakePayload = {
  resource_name: string;
  resource_kind: string;
  content: string;
  notes: string;
  building_id?: string;
  apply: boolean;
};

type IntakeResponse = {
  status: "accepted" | "rejected" | "written" | "dry_run";
  reason: string;
  building_id: string;
  patch_preview?: string | null;
  trace: AgentTrace;
};

type PatchResponse = {
  status: "dry_run" | "written" | "blocked";
  reason: string;
  building_id: string;
  patch_preview: string;
  trace: AgentTrace;
};

type RollbackPreviewResponse = {
  status: "preview" | "blocked";
  reason: string;
  event_id: string;
  building_id: string;
  patch_preview: string;
  trace: AgentTrace;
};

type RollbackResponse = {
  status: "rolled_back" | "blocked";
  reason: string;
  event_id: string;
  building_id: string;
  trace: AgentTrace;
};

type AuditEvent = {
  event_id: string;
  created_at: string;
  building_id: string;
  mode: string;
  intent: string;
  result_status: string;
  result_summary: string;
  before_snapshot?: string | null;
};

type DiffColumns = {
  before: string[];
  after: string[];
};

const starterQuestions = [
  "What unresolved financial anomalies exist?",
  "Who owns WE 01?",
  "Who are the main service providers?",
  "What open operational topics are active?"
];

const writeExamples = [
  "Add note: Heating contractor confirmed a follow-up appointment for 2026-04-27.",
  "Remember: WE 01 owner asked for a payment status review after the next bank import.",
  "Save context: Stairwell light repair should be checked during the next inspection."
];

const initialThread = (): ChatThread => ({
  id: crypto.randomUUID(),
  title: "New context chat",
  createdAt: new Date().toISOString(),
  messages: [
    {
      id: crypto.randomUUID(),
      role: "assistant",
      content: "Ask me about the compiled property context. I will search the artifact and answer from evidence.",
      createdAt: new Date().toISOString()
    }
  ]
});

async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) }
  });
  const text = await response.text();
  if (!response.ok) {
    throw new Error(text || response.statusText);
  }
  const contentType = response.headers.get("content-type") || "";
  return (contentType.includes("application/json") ? JSON.parse(text) : text) as T;
}

function BuenaLogo() {
  return (
    <span className="headline-logo" aria-hidden="true">
      <svg xmlns="http://www.w3.org/2000/svg" width="38" height="38" fill="none" viewBox="0 0 38 38">
        <path
          fill="currentColor"
          fillRule="evenodd"
          d="M19 0c1.147 0 2.1.885 2.185 2.03l.068.917a10.44 10.44 0 0 1 4.2-.876c5.786 0 10.476 4.69 10.476 10.476a10.44 10.44 0 0 1-.877 4.2l.919.068a2.19 2.19 0 0 1 0 4.37l-.918.068a10.44 10.44 0 0 1 .876 4.2c0 5.786-4.69 10.476-10.476 10.476a10.44 10.44 0 0 1-4.2-.877l-.068.919a2.19 2.19 0 0 1-4.37 0l-.068-.918a10.44 10.44 0 0 1-4.2.876c-5.786 0-10.476-4.69-10.476-10.476 0-1.494.313-2.914.876-4.2l-.918-.068a2.191 2.191 0 0 1 0-4.37l.918-.068a10.44 10.44 0 0 1-.876-4.2c0-5.786 4.69-10.476 10.476-10.476 1.493 0 2.914.313 4.2.876l.068-.918A2.191 2.191 0 0 1 19 0ZM7.924 19l-1.38 1.762a7.573 7.573 0 0 0-1.615 4.691 7.618 7.618 0 0 0 7.618 7.618 7.573 7.573 0 0 0 4.691-1.615L19 30.076l1.762 1.38a7.573 7.573 0 0 0 4.691 1.615 7.618 7.618 0 0 0 7.618-7.618 7.573 7.573 0 0 0-1.615-4.691L30.076 19l1.38-1.762a7.573 7.573 0 0 0 1.615-4.691 7.618 7.618 0 0 0-7.618-7.618 7.573 7.573 0 0 0-4.691 1.615L19 7.924l-1.762-1.38a7.573 7.573 0 0 0-4.691-1.615 7.618 7.618 0 0 0-7.618 7.618 7.57 7.57 0 0 0 1.615 4.691L7.924 19Z"
          clipRule="evenodd"
        />
      </svg>
    </span>
  );
}

function Icon({ name }: { name: IconName }) {
  const common = { fill: "none", stroke: "currentColor", strokeLinecap: "square" as const, strokeWidth: 1.7 };
  const paths: Record<IconName, ReactElement> = {
    resource: (
      <>
        <path {...common} d="M12 3v18M3 12h18" />
        <path {...common} d="M5 5h14v14H5z" />
      </>
    ),
    mechanism: (
      <>
        <path {...common} d="M4 6h5v5H4zM15 4h5v5h-5zM15 15h5v5h-5zM9 8h3l3-2M9 10l6 7" />
      </>
    ),
    theme: (
      <>
        <path {...common} d="M12 3a9 9 0 1 0 9 9 7 7 0 0 1-9-9Z" />
      </>
    ),
    threads: (
      <>
        <path {...common} d="M4 6h16M4 12h12M4 18h16" />
      </>
    ),
    newThread: (
      <>
        <path {...common} d="M5 6h14v12H5zM12 9v6M9 12h6" />
      </>
    ),
    trace: (
      <>
        <path {...common} d="M5 12h4l2-5 3 10 2-5h3" />
      </>
    ),
    context: (
      <>
        <path {...common} d="M6 4h10l2 2v14H6zM9 9h6M9 13h6M9 17h4" />
      </>
    ),
    patch: (
      <>
        <path {...common} d="M7 5h10v14H7zM10 9h4M10 12h4M10 15h2" />
        <path {...common} d="M17 5l-3 3h3z" />
      </>
    ),
    edit: (
      <>
        <path {...common} d="M5 18l4-1 9-9-3-3-9 9-1 4zM13 7l3 3" />
      </>
    ),
    save: (
      <>
        <path {...common} d="M5 5h14v14H5zM8 5v5h8M8 19v-6h8v6" />
      </>
    ),
    cancel: (
      <>
        <path {...common} d="M6 6l12 12M18 6 6 18" />
      </>
    ),
    latest: (
      <>
        <path {...common} d="M6 7v5h5M6.5 12A6 6 0 1 0 8 7.8" />
      </>
    ),
    rollback: (
      <>
        <path {...common} d="M9 7H5v4M5.5 11A7 7 0 1 0 8 5.8" />
      </>
    ),
    send: (
      <>
        <path {...common} d="M4 12 20 5l-7 16-2-7-7-2z" />
      </>
    ),
    preview: (
      <>
        <path {...common} d="M3 12s3-5 9-5 9 5 9 5-3 5-9 5-9-5-9-5z" />
        <path {...common} d="M10 12a2 2 0 1 0 4 0 2 2 0 0 0-4 0z" />
      </>
    ),
    apply: (
      <>
        <path {...common} d="M5 12l5 5L20 7" />
      </>
    ),
    close: (
      <>
        <path {...common} d="M6 6l12 12M18 6 6 18" />
      </>
    )
  };
  return (
    <svg className="icon" aria-hidden="true" viewBox="0 0 24 24">
      {paths[name]}
    </svg>
  );
}

function IconButton({
  icon,
  label,
  active = false,
  className = "",
  ...props
}: {
  icon: IconName;
  label: string;
  active?: boolean;
  className?: string;
} & ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      {...props}
      aria-label={label}
      className={`icon-button tooltip ${active ? "active" : ""} ${className}`}
      data-tip={label}
      title={label}
    >
      <Icon name={icon} />
    </button>
  );
}

function splitUnifiedDiff(diff: string): DiffColumns {
  const before: string[] = [];
  const after: string[] = [];
  for (const rawLine of diff.split("\n")) {
    if (!rawLine || rawLine.startsWith("@@") || rawLine.startsWith("---") || rawLine.startsWith("+++")) {
      continue;
    }
    if (rawLine.startsWith("-")) {
      before.push(rawLine.slice(1) || " ");
      after.push("");
      continue;
    }
    if (rawLine.startsWith("+")) {
      before.push("");
      after.push(rawLine.slice(1) || " ");
      continue;
    }
    const clean = rawLine.startsWith(" ") ? rawLine.slice(1) : rawLine;
    before.push(clean);
    after.push(clean);
  }
  return { before, after };
}

export default function Home() {
  const [theme, setTheme] = useState<Theme>("dark");
  const [busy, setBusy] = useState(false);
  const [contextText, setContextText] = useState("");
  const [latestPatch, setLatestPatch] = useState<unknown>(null);
  const [resources, setResources] = useState<ResourceRecord[]>([]);
  const [artifactView, setArtifactView] = useState<ArtifactView>("context");
  const [editingContext, setEditingContext] = useState(false);
  const [contextDraft, setContextDraft] = useState("");
  const [contextEditStatus, setContextEditStatus] = useState(
    "NOTE: Human corrections saved here become protected context and are wrapped in <user> tags."
  );
  const [threads, setThreads] = useState<ChatThread[]>([]);
  const [activeThreadId, setActiveThreadId] = useState("");
  const [threadDrawerOpen, setThreadDrawerOpen] = useState(false);
  const [question, setQuestion] = useState("");
  const [agentNote, setAgentNote] = useState("Agent reads context, plans retrieval, then answers from evidence.");
  const [agentTrace, setAgentTrace] = useState<AgentTrace>({ nodes: [] });
  const [traceExpanded, setTraceExpanded] = useState(false);
  const [citations, setCitations] = useState<AgentCitation[]>([]);
  const [activeBuilding, setActiveBuilding] = useState("LIE-001");
  const [resourceOpen, setResourceOpen] = useState(false);
  const [resourceKind, setResourceKind] = useState("email");
  const [resourceName, setResourceName] = useState("");
  const [resourceContent, setResourceContent] = useState("");
  const [resourceNotes, setResourceNotes] = useState("");
  const [resourceStatus, setResourceStatus] = useState("Paste a resource to preview the agent write.");
  const [diffTitle, setDiffTitle] = useState("");
  const [diffPreview, setDiffPreview] = useState("");
  const [pendingAction, setPendingAction] = useState<PendingAction | null>(null);
  const [pendingIntake, setPendingIntake] = useState<IntakePayload | null>(null);
  const [rollbackEventId, setRollbackEventId] = useState("");
  const [rollbackStatus, setRollbackStatus] = useState("Preview the latest writable event before rollback.");
  const dialogRef = useRef<HTMLDialogElement>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const contextHighlightRef = useRef<HTMLSpanElement | null>(null);
  const traceCollapseTimerRef = useRef<number | null>(null);
  const [contextHighlight, setContextHighlight] = useState("");

  const activeThread = useMemo(
    () => threads.find((thread) => thread.id === activeThreadId) || threads[0],
    [activeThreadId, threads]
  );

  const artifactText = useMemo(() => {
    if (artifactView === "patch") {
      return latestPatch ? JSON.stringify(latestPatch, null, 2) : "No patch log loaded yet.";
    }
    return contextText || "The compiled markdown will appear here.";
  }, [artifactView, contextText, latestPatch]);

  const diffColumns = useMemo(() => splitUnifiedDiff(diffPreview), [diffPreview]);

  useEffect(() => {
    const storedTheme = window.localStorage.getItem("buena-theme") as Theme | null;
    const initialTheme = storedTheme === "light" || storedTheme === "dark" ? storedTheme : "dark";
    setTheme(initialTheme);
    document.documentElement.dataset.theme = initialTheme;

    try {
      const storedThreads = window.localStorage.getItem("buena-chat-threads");
      const storedActiveThreadId = window.localStorage.getItem("buena-active-thread-id");
      if (storedThreads) {
        const parsed = JSON.parse(storedThreads) as ChatThread[];
        if (parsed.length) {
          setThreads(parsed);
          setActiveThreadId(parsed.some((thread) => thread.id === storedActiveThreadId) ? storedActiveThreadId || parsed[0].id : parsed[0].id);
          return;
        }
      }
    } catch {
      window.localStorage.removeItem("buena-chat-threads");
      window.localStorage.removeItem("buena-active-thread-id");
    }
    const thread = initialThread();
    setThreads([thread]);
    setActiveThreadId(thread.id);
  }, []);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    window.localStorage.setItem("buena-theme", theme);
  }, [theme]);

  useEffect(() => {
    if (threads.length) {
      window.localStorage.setItem("buena-chat-threads", JSON.stringify(threads));
    }
  }, [threads]);

  useEffect(() => {
    if (activeThreadId) {
      window.localStorage.setItem("buena-active-thread-id", activeThreadId);
    }
  }, [activeThreadId]);

  useEffect(() => {
    if (!contextHighlight) {
      return;
    }
    contextHighlightRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [contextHighlight, contextText]);

  useEffect(() => {
    if (!dialogRef.current) {
      return;
    }
    if (resourceOpen && !dialogRef.current.open) {
      dialogRef.current.showModal();
    }
    if (!resourceOpen && dialogRef.current.open) {
      dialogRef.current.close();
    }
  }, [resourceOpen]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [activeThread?.messages]);

  useEffect(() => {
    void refreshEverything();
  }, []);

  async function refreshEverything() {
    setBusy(true);
    try {
      await Promise.all([loadPatches(), loadResources(), loadContext()]);
    } finally {
      setBusy(false);
    }
  }

  async function loadContext() {
    try {
      const text = await api<string>("/api/context");
      setContextText(text);
    } catch (error) {
      setContextText(error instanceof Error ? error.message : "Context could not be loaded.");
    }
  }

  async function loadPatches() {
    const result = await api<{ patches: PatchFile[]; latest: unknown }>("/api/patches");
    setLatestPatch(result.latest);
  }

  async function loadResources() {
    const result = await api<{ resources: ResourceRecord[] }>("/api/resources");
    setResources(result.resources || []);
  }

  function persistThreads(nextThreads: ChatThread[]) {
    setThreads(nextThreads);
    window.localStorage.setItem("buena-chat-threads", JSON.stringify(nextThreads));
  }

  function startLiveTrace(labels: string[], activeLabel = "Working...") {
    if (traceCollapseTimerRef.current) {
      window.clearTimeout(traceCollapseTimerRef.current);
      traceCollapseTimerRef.current = null;
    }
    setTraceExpanded(true);
    const render = (activeIndex: number) => {
      setAgentTrace({
        nodes: labels.map((label, index) => ({
          id: `live-${label}-${index}`,
          label,
          status: index < activeIndex ? "ok" : index === activeIndex ? "info" : "blocked",
          detail:
            index < activeIndex
              ? "Completed."
              : index === activeIndex
                ? activeLabel
                : "Waiting for upstream agent step."
        }))
      });
    };
    render(0);
    const timers = labels.slice(1).map((_, index) => window.setTimeout(() => render(index + 1), (index + 1) * 450));
    return () => timers.forEach((timer) => window.clearTimeout(timer));
  }

  function finishTrace(trace: AgentTrace) {
    setAgentTrace(trace);
    if (traceCollapseTimerRef.current) {
      window.clearTimeout(traceCollapseTimerRef.current);
    }
    traceCollapseTimerRef.current = window.setTimeout(() => {
      setTraceExpanded(false);
      traceCollapseTimerRef.current = null;
    }, 1400);
  }

  function updateActiveThread(updater: (thread: ChatThread) => ChatThread) {
    setThreads((current) => {
      const next = current.map((thread) => {
        if (thread.id !== activeThreadId) {
          return thread;
        }
        return updater(thread);
      });
      window.localStorage.setItem("buena-chat-threads", JSON.stringify(next));
      return next;
    });
  }

  function createThread() {
    const thread = initialThread();
    persistThreads([thread, ...threads]);
    setActiveThreadId(thread.id);
    window.localStorage.setItem("buena-active-thread-id", thread.id);
    setQuestion("");
  }

  function parseChatWriteCommand(value: string) {
    const match = value.match(/^\s*(add note|remember|write|save context|update context|add to context)\s*:?\s+([\s\S]+)/i);
    if (!match) {
      return null;
    }
    const content = match[2].trim();
    if (content.length < 10) {
      return null;
    }
    const lowered = content.toLowerCase();
    let targetSection = "Open Operational Topics";
    if (/(invoice|payment|bank|financial|unpaid)/.test(lowered)) {
      targetSection = "Financial State";
    } else if (/(vendor|provider|contractor|service)/.test(lowered)) {
      targetSection = "Service Providers";
    } else if (/(meeting|decision|resolution|etv)/.test(lowered)) {
      targetSection = "Meetings And Decisions";
    } else if (/(email|letter|message|communication)/.test(lowered)) {
      targetSection = "Recent Communications";
    }
    return {
      content,
      targetSection,
      reason: `chat write: ${match[1].toLowerCase()}`
    };
  }

  function renderArtifactText() {
    if (artifactView !== "context" || !contextHighlight || !artifactText.includes(contextHighlight)) {
      return artifactText;
    }
    const firstIndex = artifactText.indexOf(contextHighlight);
    const before = artifactText.slice(0, firstIndex);
    const after = artifactText.slice(firstIndex + contextHighlight.length);
    return (
      <>
        {before}
        <mark className="context-highlight" ref={contextHighlightRef}>
          {contextHighlight}
        </mark>
        {after}
      </>
    );
  }

  async function askQuestion(event?: FormEvent<HTMLFormElement>, nextQuestion = question) {
    event?.preventDefault();
    const cleanQuestion = nextQuestion.trim();
    if (!cleanQuestion || !activeThread) {
      return;
    }
    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: cleanQuestion,
      createdAt: new Date().toISOString()
    };
    const pendingMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "assistant",
      content: "Thinking through the context agent...",
      createdAt: new Date().toISOString()
    };
    updateActiveThread((thread) => ({
      ...thread,
      title: thread.messages.length <= 1 ? cleanQuestion.slice(0, 46) : thread.title,
      messages: [...thread.messages, userMessage, pendingMessage]
    }));
    setQuestion("");
    setBusy(true);
    const writeCommand = parseChatWriteCommand(cleanQuestion);
    const stopTrace = writeCommand
      ? startLiveTrace(["route_building", "permission_gate", "write_context_patch", "refresh_artifact"], "Writing approved chat note...")
      : startLiveTrace(["route_building", "search_context", "citations", "answer"], "Routing question...");
    try {
      if (writeCommand) {
        const result = await writeFromChat(writeCommand.content, writeCommand.targetSection, writeCommand.reason);
        stopTrace();
        finishTrace(result.trace);
        setActiveBuilding(result.building_id);
        setArtifactView("context");
        setEditingContext(false);
        await loadContext();
        setContextHighlight(writeCommand.content);
        const responseText =
          result.status === "written"
            ? `Saved to ${writeCommand.targetSection}. I highlighted the new context in the artifact panel.`
            : `I could not write that yet: ${result.reason}`;
        updateActiveThread((thread) => ({
          ...thread,
          messages: thread.messages.map((message) => (message.id === pendingMessage.id ? { ...message, content: responseText } : message))
        }));
        return;
      }
      const result = await askAgent(cleanQuestion);
      stopTrace();
      const titles = result.citations?.length
        ? `Citations: ${result.citations.map((citation) => citation.title).join(", ")}`
        : result.agent?.evidence_titles?.length
          ? `Evidence: ${result.agent.evidence_titles.join(", ")}`
          : "";
      const modelNode = result.trace?.nodes.find((node) => node.label === "model_synthesis");
      setActiveBuilding(result.building_id || "LIE-001");
      setCitations(result.citations || []);
      finishTrace(result.trace || legacyTrace(result));
      setAgentNote(
        [
          result.building_id ? `building ${result.building_id}` : "",
          result.routed ? "auto-routed" : "",
          result.plan?.intent || result.agent?.intent,
          result.plan?.mode || result.agent?.mode,
          modelNode?.status === "ok" ? `AI synthesis: ${modelNode.detail}` : "",
          modelNode?.status === "blocked" ? `AI fallback: ${modelNode.detail}` : "",
          titles
        ]
          .filter(Boolean)
          .join(" / ")
      );
      updateActiveThread((thread) => ({
        ...thread,
        messages: thread.messages.map((message) =>
          message.id === pendingMessage.id ? { ...message, content: result.answer } : message
        )
      }));
    } catch (error) {
      updateActiveThread((thread) => ({
        ...thread,
        messages: thread.messages.map((message) =>
          message.id === pendingMessage.id
            ? { ...message, content: error instanceof Error ? error.message : "Question failed." }
            : message
        )
      }));
    } finally {
      stopTrace();
      setBusy(false);
    }
  }

  async function askAgent(cleanQuestion: string): Promise<AskResponse> {
    try {
      return await api<AskResponse>("/api/v1/agents/chat", {
        method: "POST",
        headers: { "X-Agent-Role": "viewer" },
        body: JSON.stringify({ question: cleanQuestion, building_id: "auto", use_ai: true })
      });
    } catch {
      return await api<AskResponse>("/api/ask", {
        method: "POST",
        body: JSON.stringify({ question: cleanQuestion, use_ai: true })
      });
    }
  }

  async function writeFromChat(content: string, targetSection: string, reason: string): Promise<PatchResponse> {
    return await api<PatchResponse>("/api/v1/agents/patch", {
      method: "POST",
      headers: { "X-Agent-Role": "approver" },
      body: JSON.stringify({
        building_id: activeBuilding || "LIE-001",
        target_section: targetSection,
        content: `- Chat note: ${content}`,
        reason,
        apply: true
      })
    });
  }

  function legacyTrace(result: AskResponse): AgentTrace {
    const titles = result.agent?.evidence_titles || [];
    return {
      nodes: [
        {
          id: "agent",
          label: "context_chat_agent",
          status: "info",
          detail: result.agent?.intent ? `Intent: ${result.agent.intent}` : "Legacy context agent"
        },
        {
          id: "retrieve",
          label: "retrieve_evidence",
          status: titles.length ? "ok" : "blocked",
          detail: `${titles.length} section(s) retrieved.`,
          tool: "retrieve_evidence"
        },
        {
          id: "answer",
          label: "answer",
          status: "ok",
          detail: result.agent?.mode || "natural-language response"
        }
      ]
    };
  }

  function beginContextEdit() {
    setArtifactView("context");
    setEditingContext(true);
    setContextDraft(contextText);
    setContextEditStatus("Editing context.md directly. Changed lines will be saved inside protected <user> tags.");
  }

  function cancelContextEdit() {
    setEditingContext(false);
    setContextDraft("");
    setContextEditStatus("NOTE: Human corrections saved here become protected context and are wrapped in <user> tags.");
  }

  async function saveContextEdit() {
    if (!contextDraft.trim()) {
      setContextEditStatus("Context cannot be empty.");
      return;
    }
    setBusy(true);
    setContextEditStatus("Saving artifact edit with protected <user> tags...");
    try {
      const result = await api<{ content: string; message: string }>("/api/context", {
        method: "PUT",
        body: JSON.stringify({ content: contextDraft, author: "nextjs-user" })
      });
      setContextText(result.content);
      setEditingContext(false);
      setContextDraft("");
      setContextEditStatus(result.message);
    } catch (error) {
      setContextEditStatus(error instanceof Error ? error.message : "Context save failed.");
    } finally {
      setBusy(false);
    }
  }

  async function previewResourceWrite(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault();
    if (!resourceContent.trim()) {
      setResourceStatus("Paste content or choose a readable text file first.");
      return;
    }
    setBusy(true);
    setDiffPreview("");
    setPendingAction(null);
    setPendingIntake(null);
    const stopTrace = startLiveTrace(["route_building", "validate_resource", "dry_run_context_patch"], "Checking resource...");
    setResourceStatus("Agent is validating the resource and preparing a dry-run patch...");
    const payload: IntakePayload = {
      resource_name: resourceName.trim() || `${resourceKind}-resource.txt`,
      resource_kind: resourceKind,
      content: resourceContent,
      notes: resourceNotes,
      building_id: activeBuilding || undefined,
      apply: false
    };
    try {
      const result = await api<IntakeResponse>("/api/v1/agents/intake", {
        method: "POST",
        headers: { "X-Agent-Role": "editor" },
        body: JSON.stringify(payload)
      });
      stopTrace();
      finishTrace(result.trace);
      setActiveBuilding(result.building_id);
      setDiffTitle(`Proposed write for ${result.building_id}`);
      setDiffPreview(result.patch_preview || "");
      if (result.status === "dry_run" && result.patch_preview) {
        setPendingAction("intake");
        setPendingIntake({ ...payload, building_id: result.building_id, apply: true });
        setResourceStatus("Dry-run ready. Review the before/after diff, then apply the approved write.");
        return;
      }
      setResourceStatus(result.reason);
    } catch (error) {
      setResourceStatus(error instanceof Error ? error.message : "Agent dry-run failed.");
    } finally {
      stopTrace();
      setBusy(false);
    }
  }

  async function applyPendingAction() {
    if (!pendingAction) {
      return;
    }
    setBusy(true);
    let stopTrace = () => {};
    try {
      if (pendingAction === "intake" && pendingIntake) {
        stopTrace = startLiveTrace(["permission_gate", "write_context_patch", "audit_event"], "Applying approved write...");
        const result = await api<IntakeResponse>("/api/v1/agents/intake", {
          method: "POST",
          headers: { "X-Agent-Role": "approver" },
          body: JSON.stringify(pendingIntake)
        });
        stopTrace();
        finishTrace(result.trace);
        setArtifactView("context");
        setContextHighlight(pendingIntake.content.split(/\s+/).slice(0, 12).join(" "));
        setResourceStatus(result.status === "written" ? "Approved write saved to context.md." : result.reason);
        setDiffPreview("");
        setPendingAction(null);
        setPendingIntake(null);
        setResourceName("");
        setResourceContent("");
        setResourceNotes("");
        await Promise.all([loadResources(), loadContext(), loadPatches()]);
        return;
      }
      if (pendingAction === "rollback" && rollbackEventId.trim()) {
        stopTrace = startLiveTrace(["permission_gate", "rollback_context", "refresh_context"], "Applying rollback...");
        const result = await api<RollbackResponse>("/api/v1/agents/rollback", {
          method: "POST",
          headers: { "X-Agent-Role": "admin" },
          body: JSON.stringify({ building_id: activeBuilding, event_id: rollbackEventId.trim() })
        });
        stopTrace();
        finishTrace(result.trace);
        setRollbackStatus(result.reason);
        setDiffPreview("");
        setPendingAction(null);
        await Promise.all([loadContext(), loadPatches()]);
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Approved action failed.";
      pendingAction === "rollback" ? setRollbackStatus(message) : setResourceStatus(message);
    } finally {
      stopTrace();
      setBusy(false);
    }
  }

  async function previewRollback(eventId = rollbackEventId.trim()) {
    if (!eventId) {
      setRollbackStatus("Add an audit event id, or load the latest writable event first.");
      return;
    }
    setBusy(true);
    const stopTrace = startLiveTrace(["lookup_audit", "rollback_preview"], "Preparing rollback preview...");
    setRollbackStatus("Generating rollback diff preview...");
    try {
      const result = await api<RollbackPreviewResponse>("/api/v1/agents/rollback-preview", {
        method: "POST",
        headers: { "X-Agent-Role": "admin" },
        body: JSON.stringify({ building_id: activeBuilding, event_id: eventId })
      });
      stopTrace();
      finishTrace(result.trace);
      setRollbackEventId(result.event_id);
      setDiffTitle(`Rollback preview for ${result.event_id}`);
      setDiffPreview(result.patch_preview);
      if (result.status === "preview" && result.patch_preview) {
        setPendingAction("rollback");
        setRollbackStatus("Rollback preview ready. Apply only if the right-hand context is the desired restored state.");
      } else {
        setPendingAction(null);
        setRollbackStatus(result.reason);
      }
    } catch (error) {
      setRollbackStatus(error instanceof Error ? error.message : "Rollback preview failed.");
    } finally {
      stopTrace();
      setBusy(false);
    }
  }

  async function loadLatestRollbackEvent() {
    setBusy(true);
    setRollbackStatus("Looking for latest writable audit event...");
    try {
      const result = await api<{ events: AuditEvent[] }>(`/api/v1/agents/audit/${activeBuilding}`);
      const latest = [...result.events].reverse().find((event) => event.before_snapshot);
      if (!latest) {
        setRollbackStatus("No rollback-capable audit event exists yet. Apply a resource write first.");
        return;
      }
      setRollbackEventId(latest.event_id);
      await previewRollback(latest.event_id);
    } catch (error) {
      setRollbackStatus(error instanceof Error ? error.message : "Audit lookup failed.");
    } finally {
      setBusy(false);
    }
  }

  async function readResourceFile(file: File | undefined) {
    if (!file) {
      return;
    }
    setResourceName((current) => current || file.name);
    try {
      setResourceContent(await file.text());
      setResourceStatus(`${file.name} loaded locally. Review, then preview the agent write.`);
    } catch {
      setResourceStatus(`Could not read ${file.name}. Paste extracted text instead.`);
    }
  }

  return (
    <main className={`page-shell ${busy ? "busy" : ""}`}>
      <header className="fixed-header">
        <h1 className="headline">
          <span className="headline-line">
            <span>Context Engine</span>
            <BuenaLogo />
            <span>Runs On.</span>
          </span>
        </h1>
      </header>

      <section className="stage">
        <div className="grid-frame" aria-hidden="true" />
        <div className="app-shell">
          <div className="app-chrome">
            <span className="chrome-dots" aria-hidden="true" />
            <span className="chrome-title">
              <strong>APP.BUENA.CONTEXT</strong>
              <em>One living context for the property.</em>
            </span>
            <span className="app-actions">
              <a className="icon-button tooltip" data-tip="Working mechanism" href="/mechanism" title="Working mechanism">
                <Icon name="mechanism" />
              </a>
              <IconButton icon="resource" label="Add resource" type="button" onClick={() => setResourceOpen(true)} />
              <IconButton
                icon="theme"
                label={theme === "dark" ? "Switch to light" : "Switch to dark"}
                type="button"
                onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
              />
            </span>
          </div>

          <section className="content-grid">
            <section className="answer-panel chat-panel">
              <div className="panel-head">
                <div>
                  <h3>Context chatbot</h3>
                </div>
                <IconButton
                  icon="threads"
                  label={threadDrawerOpen ? "Hide threads" : "Show threads"}
                  type="button"
                  onClick={() => setThreadDrawerOpen((open) => !open)}
                />
              </div>

              <div className={`thread-drawer ${threadDrawerOpen ? "open" : ""}`} aria-hidden={!threadDrawerOpen}>
                <IconButton icon="newThread" label="New thread" type="button" onClick={createThread} />
                {threads.map((thread) => (
                  <button
                    className={`thread-item ${thread.id === activeThreadId ? "active" : ""}`}
                    key={thread.id}
                    type="button"
                    onClick={() => setActiveThreadId(thread.id)}
                  >
                    {thread.title}
                  </button>
                ))}
              </div>

              <div className="chat-window">
                {activeThread?.messages.map((message) => (
                  <article className={`chat-message ${message.role}`} key={message.id}>
                    <span>{message.role === "user" ? "You" : "Agent"}</span>
                    <p>{message.content}</p>
                  </article>
                ))}
                <div ref={chatEndRef} />
              </div>

              <section className={`trace-panel ${traceExpanded ? "expanded" : "collapsed"}`} aria-label="Agent visual trace">
                <div className="trace-head">
                  <span>Agent trace</span>
                  <strong>{activeBuilding}</strong>
                  <IconButton
                    icon="trace"
                    label={traceExpanded ? "Collapse trace" : "Show trace"}
                    type="button"
                    onClick={() => setTraceExpanded((open) => !open)}
                  />
                </div>
                {traceExpanded ? (
                  <div className="trace-line">
                    {(agentTrace.nodes.length
                      ? agentTrace.nodes
                      : [{ id: "idle", label: "ready", status: "info", detail: "Ask a question to see the agent path." } as AgentTraceNode]
                    ).map((node, index) => (
                      <div className={`trace-node ${node.status}`} key={node.id} title={node.detail}>
                        <span>{String(index + 1).padStart(2, "0")}</span>
                        <strong>{node.label}</strong>
                        <p>{node.detail}</p>
                      </div>
                    ))}
                  </div>
                ) : null}
                {traceExpanded && citations.length ? (
                  <div className="citation-grid">
                    {citations.slice(0, 3).map((citation) => (
                      <article key={`${citation.rank}-${citation.title}`}>
                        <span>
                          [{citation.rank}] {citation.title}
                        </span>
                        <p>{citation.quote}</p>
                      </article>
                    ))}
                  </div>
                ) : null}
              </section>

              <div className="prompt-bank" aria-label="Example questions">
                {starterQuestions.map((item) => (
                  <button key={item} type="button" onClick={() => void askQuestion(undefined, item)} disabled={busy}>
                    {item.replace("What unresolved ", "").replace("Who are the main ", "")}
                  </button>
                ))}
                {writeExamples.map((item) => (
                  <button className="write-example" key={item} type="button" onClick={() => void askQuestion(undefined, item)} disabled={busy}>
                    {item.split(":")[0]} context
                  </button>
                ))}
              </div>

              <form className="ask-box" onSubmit={askQuestion}>
                <input
                  value={question}
                  onChange={(event) => setQuestion(event.target.value)}
                  placeholder="Ask the agent about owners, invoices, risks, topics..."
                />
                <IconButton icon="send" label="Send message" type="submit" disabled={busy} />
              </form>
              <p className="agent-note">{agentNote}</p>
            </section>

            <section className="context-panel">
              <div className="panel-head context-head">
                <div>
                  <p className="eyebrow">Artifact</p>
                  <h3>context.md preview and edit</h3>
                </div>
                <div className="context-tools">
                  <IconButton
                    icon="context"
                    label="Show context"
                    active={artifactView === "context"}
                    type="button"
                    onClick={() => {
                      setArtifactView("context");
                      setEditingContext(false);
                    }}
                  />
                  <IconButton
                    icon="patch"
                    label="Show latest patch"
                    active={artifactView === "patch"}
                    type="button"
                    onClick={() => {
                      setArtifactView("patch");
                      setEditingContext(false);
                    }}
                  />
                  {artifactView === "context" && !editingContext ? (
                    <IconButton icon="edit" label="Edit context" type="button" onClick={beginContextEdit} />
                  ) : null}
                  {artifactView === "context" && editingContext ? (
                    <>
                      <IconButton
                        icon="save"
                        label="Save with user tags"
                        active
                        type="button"
                        onClick={() => void saveContextEdit()}
                        disabled={busy}
                      />
                      <IconButton icon="cancel" label="Cancel edit" type="button" onClick={cancelContextEdit} />
                    </>
                  ) : null}
                </div>
              </div>
              <div className="context-edit-status">{contextEditStatus}</div>
              <div className="rollback-strip">
                <input
                  value={rollbackEventId}
                  onChange={(event) => setRollbackEventId(event.target.value)}
                  placeholder="Audit event id for rollback preview"
                />
                <IconButton icon="latest" label="Load latest rollback event" type="button" onClick={() => void loadLatestRollbackEvent()} disabled={busy} />
                <IconButton icon="rollback" label="Preview rollback" type="button" onClick={() => void previewRollback()} disabled={busy} />
              </div>
              <p className="rollback-status">{rollbackStatus}</p>
              {editingContext ? (
                <textarea
                  className="context-editor"
                  spellCheck={false}
                  value={contextDraft}
                  onChange={(event) => setContextDraft(event.target.value)}
                  aria-label="Editable context.md artifact"
                />
              ) : (
                <pre className="context-preview">{renderArtifactText()}</pre>
              )}
            </section>
          </section>
        </div>
      </section>

      <dialog
        ref={dialogRef}
        className="resource-dialog"
        onCancel={(event) => {
          event.preventDefault();
          setResourceOpen(false);
        }}
        onClose={() => setResourceOpen(false)}
      >
        <div className="dialog-head">
          <div>
            <p className="eyebrow">Resource Intake</p>
            <h3>Add email, text, or file</h3>
          </div>
          <IconButton icon="close" label="Close resource intake" type="button" onClick={() => setResourceOpen(false)} />
        </div>
        <p className="helper-copy">The agent validates the resource, previews the context diff, then waits for approval.</p>
        <form className="stack-form" onSubmit={previewResourceWrite}>
          <div className="split-row">
            <select value={resourceKind} onChange={(event) => setResourceKind(event.target.value)} aria-label="Resource type">
              <option value="email">Email</option>
              <option value="text">Plain text</option>
              <option value="letter">Letter</option>
              <option value="invoice">Invoice</option>
              <option value="bank">Bank record</option>
              <option value="other">Other</option>
            </select>
            <input
              value={resourceName}
              onChange={(event) => setResourceName(event.target.value)}
              type="text"
              placeholder="Name or subject"
            />
          </div>
          <label className="file-drop">
            <input type="file" onChange={(event) => void readResourceFile(event.target.files?.[0])} />
            <span>Choose a file or paste content below</span>
          </label>
          <textarea
            rows={7}
            value={resourceContent}
            onChange={(event) => setResourceContent(event.target.value)}
            placeholder="Paste email body, notes, extracted PDF text, CSV rows, or any source text..."
          />
          <input
            type="text"
            value={resourceNotes}
            onChange={(event) => setResourceNotes(event.target.value)}
            placeholder="Optional note for the future ingestion agent"
          />
          <div className="button-row">
            <IconButton icon="preview" label="Preview agent write" type="submit" disabled={busy} />
            <IconButton
              icon="apply"
              label="Apply approved write"
              active
              type="button"
              onClick={() => void applyPendingAction()}
              disabled={busy || pendingAction !== "intake"}
            />
          </div>
        </form>
        <div className="soft-status">{resourceStatus}</div>
        {diffPreview ? (
          <section className="diff-panel" aria-label="Agent diff preview">
            <div className="diff-head">
              <span>{diffTitle || "Diff preview"}</span>
              {pendingAction === "rollback" ? (
                <IconButton icon="apply" label="Apply rollback" active type="button" onClick={() => void applyPendingAction()} disabled={busy} />
              ) : null}
            </div>
            <div className="diff-grid">
              <div>
                <strong>Before</strong>
                <pre>
                  {diffColumns.before.map((line, index) => (
                    <span className={line ? "diff-line remove" : "diff-line empty"} key={`before-${index}`}>
                      {line || " "}
                    </span>
                  ))}
                </pre>
              </div>
              <div>
                <strong>After</strong>
                <pre>
                  {diffColumns.after.map((line, index) => (
                    <span className={line ? "diff-line add" : "diff-line empty"} key={`after-${index}`}>
                      {line || " "}
                    </span>
                  ))}
                </pre>
              </div>
            </div>
          </section>
        ) : null}
        <div className="resource-list">
          {resources.length ? (
            resources.slice(0, 4).map((resource) => (
              <div className="resource-item" key={`${resource.id || resource.name}-${resource.created_at || ""}`}>
                <span>{resource.name}</span>
                <strong>
                  {resource.kind} / {resource.status || "staged"}
                </strong>
              </div>
            ))
          ) : (
            <div className="resource-item">
              <span>No staged resources yet</span>
              <strong>ready</strong>
            </div>
          )}
        </div>
      </dialog>

      {diffPreview && !resourceOpen ? (
        <aside className="floating-diff">
          <section className="diff-panel" aria-label="Rollback diff preview">
            <div className="diff-head">
              <span>{diffTitle || "Diff preview"}</span>
              {pendingAction === "rollback" ? (
                <IconButton icon="apply" label="Apply rollback" active type="button" onClick={() => void applyPendingAction()} disabled={busy} />
              ) : null}
              <IconButton icon="close" label="Close diff preview" type="button" onClick={() => setDiffPreview("")} />
            </div>
            <div className="diff-grid">
              <div>
                <strong>Before</strong>
                <pre>
                  {diffColumns.before.map((line, index) => (
                    <span className={line ? "diff-line remove" : "diff-line empty"} key={`float-before-${index}`}>
                      {line || " "}
                    </span>
                  ))}
                </pre>
              </div>
              <div>
                <strong>After</strong>
                <pre>
                  {diffColumns.after.map((line, index) => (
                    <span className={line ? "diff-line add" : "diff-line empty"} key={`float-after-${index}`}>
                      {line || " "}
                    </span>
                  ))}
                </pre>
              </div>
            </div>
          </section>
        </aside>
      ) : null}
    </main>
  );
}
