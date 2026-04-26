"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";

type Theme = "dark" | "light";
type ArtifactView = "context" | "patch";
type Role = "user" | "assistant";

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

type ProcessedResource = {
  status: string;
};

type AskResponse = {
  answer: string;
  agent?: {
    mode?: string;
    intent?: string;
    evidence_titles?: string[];
  };
};

const starterQuestions = [
  "What unresolved financial anomalies exist?",
  "Who owns WE 01?",
  "Who are the main service providers?",
  "What open operational topics are active?",
  "Which invoices were added after the January deltas?",
  "What should a property manager review first today?"
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
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options
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
    "Human corrections saved here become protected context and are wrapped in <user> tags."
  );
  const [threads, setThreads] = useState<ChatThread[]>([]);
  const [activeThreadId, setActiveThreadId] = useState("");
  const [threadDrawerOpen, setThreadDrawerOpen] = useState(false);
  const [question, setQuestion] = useState("");
  const [agentNote, setAgentNote] = useState("Agent reads context, plans retrieval, then answers from evidence.");
  const [resourceOpen, setResourceOpen] = useState(false);
  const [resourceKind, setResourceKind] = useState("email");
  const [resourceName, setResourceName] = useState("");
  const [resourceContent, setResourceContent] = useState("");
  const [resourceNotes, setResourceNotes] = useState("");
  const [resourceStatus, setResourceStatus] = useState("Nothing staged in this browser session yet.");
  const dialogRef = useRef<HTMLDialogElement>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);

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

  useEffect(() => {
    const storedTheme = window.localStorage.getItem("buena-theme") as Theme | null;
    const initialTheme = storedTheme === "light" || storedTheme === "dark" ? storedTheme : "dark";
    setTheme(initialTheme);
    document.documentElement.dataset.theme = initialTheme;

    const storedThreads = window.localStorage.getItem("buena-chat-threads");
    if (storedThreads) {
      const parsed = JSON.parse(storedThreads) as ChatThread[];
      if (parsed.length) {
        setThreads(parsed);
        setActiveThreadId(parsed[0].id);
        return;
      }
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

  function updateActiveThread(updater: (thread: ChatThread) => ChatThread) {
    setThreads((current) =>
      current.map((thread) => {
        if (thread.id !== activeThreadId) {
          return thread;
        }
        return updater(thread);
      })
    );
  }

  function createThread() {
    const thread = initialThread();
    setThreads((current) => [thread, ...current]);
    setActiveThreadId(thread.id);
    setQuestion("");
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
    try {
      const result = await api<AskResponse>("/api/ask", {
        method: "POST",
        body: JSON.stringify({ question: cleanQuestion, use_ai: true })
      });
      const titles = result.agent?.evidence_titles?.length ? `Evidence: ${result.agent.evidence_titles.join(", ")}` : "";
      setAgentNote([result.agent?.intent, result.agent?.mode, titles].filter(Boolean).join(" / "));
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
      setBusy(false);
    }
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
    setContextEditStatus("Human corrections saved here become protected context and are wrapped in <user> tags.");
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

  async function stageResource(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!resourceContent.trim()) {
      setResourceStatus("Paste content or choose a readable text file first.");
      return;
    }
    setBusy(true);
    setResourceStatus("Staging resource...");
    try {
      const result = await api<{ resource: ResourceRecord }>("/api/resources", {
        method: "POST",
        body: JSON.stringify({
          name: resourceName.trim() || `${resourceKind}-resource.txt`,
          kind: resourceKind,
          content: resourceContent,
          notes: resourceNotes
        })
      });
      setResourceStatus(`${result.resource.name} is staged for ingestion.`);
      setResourceName("");
      setResourceContent("");
      setResourceNotes("");
      await loadResources();
    } catch (error) {
      setResourceStatus(error instanceof Error ? error.message : "Resource staging failed.");
    } finally {
      setBusy(false);
    }
  }

  async function processIntake() {
    setBusy(true);
    setResourceStatus("Agent is validating staged resources against schemas...");
    try {
      const result = await api<{ processed?: ProcessedResource[] }>("/api/process-intake", {
        method: "POST",
        body: JSON.stringify({ use_ai: true })
      });
      const processed = result.processed || [];
      const written = processed.filter((item) => item.status === "written_to_context").length;
      const rejected = processed.filter((item) => item.status === "rejected").length;
      setResourceStatus(`Agent processed ${processed.length} resource(s): ${written} written, ${rejected} rejected.`);
      await Promise.all([loadResources(), loadContext()]);
    } catch (error) {
      setResourceStatus(error instanceof Error ? error.message : "Agentic intake failed.");
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
      setResourceStatus(`${file.name} loaded locally. Review, then stage it.`);
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
        <div className="nav-row">
          <span>Buena</span>
          <button className="nav-link" type="button" onClick={() => setTheme(theme === "dark" ? "light" : "dark")}>
            {theme === "dark" ? "Light" : "Dark"}
          </button>
        </div>
      </header>

      <section className="stage">
        <div className="grid-frame" aria-hidden="true" />
        <div className="app-shell">
          <section className="top-strip">
            <div>
              <p className="eyebrow">Context</p>
              <h2>One living context for the property.</h2>
            </div>
            <button className="primary" type="button" onClick={() => setResourceOpen(true)}>
              Add resource
            </button>
          </section>

          <section className="content-grid">
            <section className="answer-panel chat-panel">
              <div className="panel-head">
                <div>
                  <p className="eyebrow">Ask</p>
                  <h3>Context chatbot</h3>
                </div>
                <button type="button" onClick={() => setThreadDrawerOpen((open) => !open)}>
                  {threadDrawerOpen ? "Hide threads" : "Threads"}
                </button>
              </div>

              <div className={`thread-drawer ${threadDrawerOpen ? "open" : ""}`} aria-hidden={!threadDrawerOpen}>
                <button className="primary" type="button" onClick={createThread}>
                  New thread
                </button>
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

              <div className="prompt-bank" aria-label="Example questions">
                {starterQuestions.map((item) => (
                  <button key={item} type="button" onClick={() => void askQuestion(undefined, item)} disabled={busy}>
                    {item.replace("What unresolved ", "").replace("Who are the main ", "")}
                  </button>
                ))}
              </div>

              <form className="ask-box" onSubmit={askQuestion}>
                <input
                  value={question}
                  onChange={(event) => setQuestion(event.target.value)}
                  placeholder="Ask the agent about owners, invoices, risks, topics..."
                />
                <button type="submit" disabled={busy}>
                  Send
                </button>
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
                  <button
                    className={`tab ${artifactView === "context" ? "active" : ""}`}
                    type="button"
                    onClick={() => {
                      setArtifactView("context");
                      setEditingContext(false);
                    }}
                  >
                    Context
                  </button>
                  <button
                    className={`tab ${artifactView === "patch" ? "active" : ""}`}
                    type="button"
                    onClick={() => {
                      setArtifactView("patch");
                      setEditingContext(false);
                    }}
                  >
                    Latest patch
                  </button>
                  {artifactView === "context" && !editingContext ? (
                    <button type="button" onClick={beginContextEdit}>
                      Edit context
                    </button>
                  ) : null}
                  {artifactView === "context" && editingContext ? (
                    <>
                      <button className="primary" type="button" onClick={() => void saveContextEdit()} disabled={busy}>
                        Save with &lt;user&gt; tags
                      </button>
                      <button type="button" onClick={cancelContextEdit}>
                        Cancel
                      </button>
                    </>
                  ) : null}
                </div>
              </div>
              <div className="context-edit-status">{contextEditStatus}</div>
              {editingContext ? (
                <textarea
                  className="context-editor"
                  spellCheck={false}
                  value={contextDraft}
                  onChange={(event) => setContextDraft(event.target.value)}
                  aria-label="Editable context.md artifact"
                />
              ) : (
                <pre className="context-preview">{artifactText}</pre>
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
          <button type="button" onClick={() => setResourceOpen(false)}>
            Close
          </button>
        </div>
        <p className="helper-copy">Stage new evidence, then let the schema-guided agent validate and write it.</p>
        <form className="stack-form" onSubmit={stageResource}>
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
            <button type="submit" disabled={busy}>
              Stage resource
            </button>
            <button className="primary" type="button" onClick={() => void processIntake()} disabled={busy}>
              Process staged
            </button>
          </div>
        </form>
        <div className="soft-status">{resourceStatus}</div>
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
    </main>
  );
}
