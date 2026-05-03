"use client";

import { useEffect, useMemo, useState } from "react";

type Theme = "dark" | "light";
type FlowKey = "ask" | "resource" | "manual" | "rollback";

type NodeId =
  | "sources"
  | "schemas"
  | "compiler"
  | "context"
  | "chat"
  | "retrieval"
  | "model"
  | "answer"
  | "resource"
  | "diff"
  | "write"
  | "user"
  | "guard"
  | "audit"
  | "rollback";

type FlowNode = {
  id: NodeId;
  title: string;
  eyebrow: string;
  x: number;
  y: number;
  detail: string;
  artifacts: string[];
};

type FlowMode = {
  key: FlowKey;
  title: string;
  summary: string;
  path: NodeId[];
};

const nodes: FlowNode[] = [
  {
    id: "sources",
    title: "Source data",
    eyebrow: "raw input",
    x: 10,
    y: 34,
    detail: "Bank rows, invoices, emails, letters, master data, and incremental folders start here.",
    artifacts: ["data/bank", "data/emails", "data/briefe", "data/incremental"]
  },
  {
    id: "schemas",
    title: "Schema contracts",
    eyebrow: "rules",
    x: 18,
    y: 12,
    detail: "Markdown schemas describe validation, parsing, rendering, patching, and chat-agent behavior.",
    artifacts: ["RESOURCE_VALIDATION_SCHEMA.md", "PATCH_SCHEMA.md", "CHAT_AGENT_SCHEMA.md"]
  },
  {
    id: "compiler",
    title: "Context compiler",
    eyebrow: "pipeline",
    x: 27,
    y: 34,
    detail: "Deterministic Python executors parse source data and compile the canonical property memory.",
    artifacts: ["bootstrap", "apply-delta", "replay-deltas"]
  },
  {
    id: "context",
    title: "Living context",
    eyebrow: "artifact",
    x: 49,
    y: 34,
    detail: "The generated context.md becomes the working memory for chat, writes, edits, and rollback.",
    artifacts: ["outputs/properties/LIE-001/context.md", "context.meta.json", "patches/*.json"]
  },
  {
    id: "chat",
    title: "User asks",
    eyebrow: "chat",
    x: 10,
    y: 67,
    detail: "A property manager asks a question or uses a write command such as Add note: ...",
    artifacts: ["frontend chat thread", "question", "actor role"]
  },
  {
    id: "retrieval",
    title: "Evidence retrieval",
    eyebrow: "tools",
    x: 27,
    y: 67,
    detail: "The agent routes to a building, searches the context, and extracts cited evidence.",
    artifacts: ["route_building", "search_context", "citations"]
  },
  {
    id: "model",
    title: "Claude",
    eyebrow: "AI synthesis",
    x: 49,
    y: 67,
    detail: "The model only synthesizes from retrieved evidence. It is not the source of truth.",
    artifacts: ["llama-3.3-70b-instruct", "model_synthesis", "safe fallback"]
  },
  {
    id: "answer",
    title: "Cited answer",
    eyebrow: "output",
    x: 73,
    y: 67,
    detail: "The UI shows the answer, citations, and visual trace so the path is explainable.",
    artifacts: ["answer", "trace.nodes", "citation cards"]
  },
  {
    id: "resource",
    title: "Resource intake",
    eyebrow: "new evidence",
    x: 73,
    y: 11,
    detail: "A user pastes or uploads a resource. The agent checks whether it is useful property evidence.",
    artifacts: ["email text", "invoice text", "plain notes"]
  },
  {
    id: "diff",
    title: "Dry-run diff",
    eyebrow: "preview",
    x: 88,
    y: 34,
    detail: "Before a resource write or rollback, the app shows a side-by-side before/after diff.",
    artifacts: ["patch_preview", "before", "after"]
  },
  {
    id: "write",
    title: "Guarded write",
    eyebrow: "mutation",
    x: 73,
    y: 34,
    detail: "Approver actions write only through registered tools and preserve protected blocks.",
    artifacts: ["write_context_patch", "permission_gate", "target section"]
  },
  {
    id: "user",
    title: "Manual edit",
    eyebrow: "human truth",
    x: 27,
    y: 88,
    detail: "Manual corrections are wrapped in user tags and treated as authoritative context.",
    artifacts: ["<user> block", "author", "timestamp"]
  },
  {
    id: "guard",
    title: "Protection guard",
    eyebrow: "safety",
    x: 49,
    y: 88,
    detail: "Before every candidate write, protected user blocks are compared. If they changed, the write is blocked.",
    artifacts: ["validate_human_authority", "extract_user_blocks", "blocked write"]
  },
  {
    id: "audit",
    title: "Audit log",
    eyebrow: "memory",
    x: 88,
    y: 67,
    detail: "Every write records role, plan, tool calls, result, and before/after snapshots.",
    artifacts: ["agent_audit", "before_snapshot", "after_snapshot"]
  },
  {
    id: "rollback",
    title: "Rollback preview",
    eyebrow: "recovery",
    x: 73,
    y: 88,
    detail: "Admin rollback first previews a diff, then restores an audited before snapshot if approved.",
    artifacts: ["rollback-preview", "rollback", "admin role"]
  }
];

const flows: FlowMode[] = [
  {
    key: "ask",
    title: "Ask a question",
    summary: "Question flows through retrieval, AI synthesis, and citations.",
    path: ["chat", "retrieval", "context", "model", "answer"]
  },
  {
    key: "resource",
    title: "Add a resource",
    summary: "New evidence is validated, previewed, guarded, written, and audited.",
    path: ["resource", "schemas", "diff", "write", "guard", "context", "audit"]
  },
  {
    key: "manual",
    title: "Manual correction",
    summary: "Human edits become protected context and guard future writes.",
    path: ["user", "guard", "context", "retrieval", "model", "answer"]
  },
  {
    key: "rollback",
    title: "Rollback safely",
    summary: "Audit snapshots power rollback preview and restore.",
    path: ["audit", "rollback", "diff", "write", "context"]
  }
];

const nodeById = new Map(nodes.map((node) => [node.id, node]));

function connectionPath(from: FlowNode, to: FlowNode) {
  const x1 = from.x + 5;
  const y1 = from.y + 3;
  const x2 = to.x + 5;
  const y2 = to.y + 3;
  const mid = (x1 + x2) / 2;
  return `M ${x1} ${y1} C ${mid} ${y1}, ${mid} ${y2}, ${x2} ${y2}`;
}

export default function MechanismPage() {
  const [theme, setTheme] = useState<Theme>("dark");
  const [activeFlow, setActiveFlow] = useState<FlowKey>("ask");
  const [activeNodeId, setActiveNodeId] = useState<NodeId>("chat");

  const selectedFlow = flows.find((flow) => flow.key === activeFlow) || flows[0];
  const selectedNode = nodeById.get(activeNodeId) || nodes[0];
  const activePath = selectedFlow.path;
  const activeConnections = useMemo(
    () =>
      activePath
        .slice(0, -1)
        .map((id, index) => [nodeById.get(id), nodeById.get(activePath[index + 1])] as const)
        .filter((pair): pair is readonly [FlowNode, FlowNode] => Boolean(pair[0] && pair[1])),
    [activePath]
  );

  useEffect(() => {
    const storedTheme = window.localStorage.getItem("buena-theme") as Theme | null;
    const initialTheme = storedTheme === "light" || storedTheme === "dark" ? storedTheme : "dark";
    setTheme(initialTheme);
    document.documentElement.dataset.theme = initialTheme;
  }, []);

  function toggleTheme() {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    document.documentElement.dataset.theme = next;
    window.localStorage.setItem("buena-theme", next);
  }

  function selectFlow(flow: FlowMode) {
    setActiveFlow(flow.key);
    setActiveNodeId(flow.path[0]);
  }

  return (
    <main className="mechanism-page">
      <header className="fixed-header">
        <h1 className="headline">
          <span className="headline-line">
            <span>Context Engine</span>
            <span className="headline-logo" aria-hidden="true">
              <svg xmlns="http://www.w3.org/2000/svg" width="38" height="38" fill="none" viewBox="0 0 38 38">
                <path
                  fill="currentColor"
                  fillRule="evenodd"
                  d="M19 0c1.147 0 2.1.885 2.185 2.03l.068.917a10.44 10.44 0 0 1 4.2-.876c5.786 0 10.476 4.69 10.476 10.476a10.44 10.44 0 0 1-.877 4.2l.919.068a2.19 2.19 0 0 1 0 4.37l-.918.068a10.44 10.44 0 0 1 .876 4.2c0 5.786-4.69 10.476-10.476 10.476a10.44 10.44 0 0 1-4.2-.877l-.068.919a2.19 2.19 0 0 1-4.37 0l-.068-.918a10.44 10.44 0 0 1-4.2.876c-5.786 0-10.476-4.69-10.476-10.476 0-1.494.313-2.914.876-4.2l-.918-.068a2.191 2.191 0 0 1 0-4.37l.918-.068a10.44 10.44 0 0 1-.876-4.2c0-5.786 4.69-10.476 10.476-10.476 1.493 0 2.914.313 4.2.876l.068-.918A2.191 2.191 0 0 1 19 0Z"
                  clipRule="evenodd"
                />
              </svg>
            </span>
            <span>Mechanism.</span>
          </span>
        </h1>
      </header>

      <section className="stage mechanism-stage">
        <div className="grid-frame" aria-hidden="true" />
        <div className="mechanism-shell flow-lab-shell">
          <div className="app-chrome">
            <span className="chrome-dots" aria-hidden="true" />
            <span className="chrome-title">
              <strong>APP.BUENA.MECHANISM</strong>
              <em>Interactive data-flow map.</em>
            </span>
            <span className="app-actions">
              <a className="icon-button tooltip" data-tip="Back to app" href="/" title="Back to app">
                <span className="mechanism-icon">A</span>
              </a>
              <button className="icon-button tooltip" data-tip="Toggle theme" type="button" onClick={toggleTheme}>
                <span className="mechanism-icon">T</span>
              </button>
            </span>
          </div>

          <section className="flow-lab-hero">
            <div>
              <p className="eyebrow">Interactive Mechanism</p>
              <h2>Watch data move from raw property records into protected context and AI answers.</h2>
            </div>
            <p>
              Choose a path, then click any node. The animated packets show how evidence, patches, user edits, and
              audit snapshots move through the system.
            </p>
          </section>

          <section className="flow-lab-controls" aria-label="Choose mechanism path">
            {flows.map((flow) => (
              <button
                className={`flow-mode ${flow.key === activeFlow ? "active" : ""}`}
                key={flow.key}
                type="button"
                onClick={() => selectFlow(flow)}
              >
                <span>{flow.key}</span>
                <strong>{flow.title}</strong>
                <em>{flow.summary}</em>
              </button>
            ))}
          </section>

          <section className="flow-lab-grid">
            <div className="flow-canvas" aria-label="Animated data flow">
              <svg className="flow-wires" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
                {activeConnections.map(([from, to], index) => {
                  const path = connectionPath(from, to);
                  return (
                    <g key={`${from.id}-${to.id}`}>
                      <path className="flow-wire" d={path} />
                      <circle className="flow-packet" r="0.9" style={{ animationDelay: `${index * 0.38}s` }}>
                        <animateMotion dur="2.8s" repeatCount="indefinite" path={path} />
                      </circle>
                    </g>
                  );
                })}
              </svg>

              {nodes.map((node) => {
                const isActive = activePath.includes(node.id);
                const isSelected = activeNodeId === node.id;
                return (
                  <button
                    className={`flow-node ${isActive ? "in-path" : ""} ${isSelected ? "selected" : ""}`}
                    key={node.id}
                    style={{ left: `${node.x}%`, top: `${node.y}%` }}
                    type="button"
                    onClick={() => setActiveNodeId(node.id)}
                  >
                    <span>{node.eyebrow}</span>
                    <strong>{node.title}</strong>
                  </button>
                );
              })}
            </div>

            <aside className="flow-inspector">
              <div>
                <p className="eyebrow">{selectedNode.eyebrow}</p>
                <h3>{selectedNode.title}</h3>
              </div>
              <p>{selectedNode.detail}</p>
              <div className="artifact-list">
                {selectedNode.artifacts.map((artifact) => (
                  <span key={artifact}>{artifact}</span>
                ))}
              </div>
              <div className="flow-progress">
                {activePath.map((nodeId, index) => {
                  const node = nodeById.get(nodeId);
                  return (
                    <button
                      className={nodeId === activeNodeId ? "active" : ""}
                      key={nodeId}
                      type="button"
                      onClick={() => setActiveNodeId(nodeId)}
                    >
                      <span>{String(index + 1).padStart(2, "0")}</span>
                      {node?.title}
                    </button>
                  );
                })}
              </div>
            </aside>
          </section>

          <section className="flow-legend">
            <article>
              <span className="legend-dot live" />
              <h3>Moving packets</h3>
              <p>Animated dots represent evidence, patches, and audit snapshots travelling between bounded tools.</p>
            </article>
            <article>
              <span className="legend-dot selected" />
              <h3>Active path</h3>
              <p>The bright nodes are the selected user journey. Switch paths to explain read, write, edit, or rollback.</p>
            </article>
            <article>
              <span className="legend-dot guard" />
              <h3>Safety gates</h3>
              <p>Writes pass through role checks, protected user-block validation, diff previews, and audit snapshots.</p>
            </article>
          </section>
        </div>
      </section>
    </main>
  );
}
