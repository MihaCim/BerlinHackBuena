"use client";

import { useEffect, useState } from "react";

type Theme = "dark" | "light";

const flows = [
  {
    name: "Read question",
    tag: "chat",
    steps: ["Route building", "Search context", "Attach citations", "Model synthesis", "Answer"]
  },
  {
    name: "Chat write",
    tag: "write",
    steps: ["Parse intent", "Permission gate", "Patch context", "Audit event", "Highlight artifact"]
  },
  {
    name: "Resource intake",
    tag: "intake",
    steps: ["Upload/paste", "Spam check", "Schema route", "Dry-run diff", "Approve write"]
  },
  {
    name: "Rollback",
    tag: "safety",
    steps: ["Find audit event", "Preview diff", "Admin gate", "Restore snapshot", "Refresh artifact"]
  }
];

const gates = [
  "Protected <user> blocks are immutable.",
  "Every write creates an audit event.",
  "Resource writes preview a diff before apply.",
  "Rollback previews the restored state first.",
  "Academic Cloud only synthesizes from retrieved evidence."
];

export default function MechanismPage() {
  const [theme, setTheme] = useState<Theme>("dark");

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
        <div className="mechanism-shell">
          <div className="app-chrome">
            <span className="chrome-dots" aria-hidden="true" />
            <span className="chrome-title">
              <strong>APP.BUENA.MECHANISM</strong>
              <em>How the property context engine works.</em>
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

          <section className="mechanism-hero">
            <div>
              <p className="eyebrow">Working Mechanism</p>
              <h2>Agents read evidence, propose changes, and protect human truth.</h2>
            </div>
            <p>
              The app is not one giant prompt. It is a bounded pipeline: deterministic tools retrieve and guard the
              context, Academic Cloud synthesizes answers when enabled, and every write passes through safety gates.
            </p>
          </section>

          <section className="mechanism-map" aria-label="Visual process map">
            {flows.map((flow) => (
              <article className="flow-card" key={flow.name}>
                <div className="flow-head">
                  <span>{flow.tag}</span>
                  <h3>{flow.name}</h3>
                </div>
                <div className="flow-rail">
                  {flow.steps.map((step, index) => (
                    <div className="flow-step" key={step}>
                      <span>{String(index + 1).padStart(2, "0")}</span>
                      <strong>{step}</strong>
                    </div>
                  ))}
                </div>
              </article>
            ))}
          </section>

          <section className="mechanism-detail-grid">
            <article>
              <p className="eyebrow">Read Path</p>
              <h3>Question to answer</h3>
              <p>
                A user asks a question. The route agent selects the building, search retrieves relevant context
                sections, citations are attached, and the configured Academic Cloud model writes a natural answer from
                only that evidence.
              </p>
            </article>
            <article>
              <p className="eyebrow">Write Path</p>
              <h3>Change to context</h3>
              <p>
                Chat write commands and resource intake never edit blindly. They target a section, generate a patch,
                preserve protected user edits, write an audit event, and refresh the artifact view.
              </p>
            </article>
            <article>
              <p className="eyebrow">Human Authority</p>
              <h3>Protected user context</h3>
              <p>
                Manual edits are wrapped in <code>&lt;user&gt;</code> tags. Before any agent write, the guard compares
                protected blocks before and after. If a block changed, the write is blocked.
              </p>
            </article>
            <article>
              <p className="eyebrow">Recovery</p>
              <h3>Preview before rollback</h3>
              <p>
                Rollback uses audit snapshots. The user previews the diff first, then an admin-level action restores the
                previous context only after review.
              </p>
            </article>
          </section>

          <section className="safety-panel">
            <div>
              <p className="eyebrow">Safety Contract</p>
              <h3>Rules every process follows</h3>
            </div>
            <div className="safety-grid">
              {gates.map((gate, index) => (
                <div className="safety-gate" key={gate}>
                  <span>{String(index + 1).padStart(2, "0")}</span>
                  <p>{gate}</p>
                </div>
              ))}
            </div>
          </section>
        </div>
      </section>
    </main>
  );
}
