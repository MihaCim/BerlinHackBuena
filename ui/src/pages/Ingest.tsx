import { useEffect, useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  fetchIncremental,
  runSimIngestStream,
  type SimDay,
  type SimIngestResponse,
  type SimItem,
  type SimStageEvent,
} from "../api";
import { cn } from "../lib/cn";

type Kind = "email" | "invoice" | "bank";
type Mode = "isolated" | "live";

type StageState = "pending" | "active" | "done" | "error" | "skipped";

type StageNode = {
  key: string;
  label: string;
  icon: (cls?: string) => React.ReactNode;
  hint: string;
};

const ICON_CLASS = "h-3.5 w-3.5";

function Icon({ d, cls }: { d: string; cls?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={cn(ICON_CLASS, cls)}
    >
      {d.split("|").map((path, i) => (
        <path key={i} d={path} />
      ))}
    </svg>
  );
}

const PIPELINE: StageNode[] = [
  {
    key: "normalize",
    label: "normalize",
    hint: "Convert raw input → markdown",
    icon: (cls) =>
      <Icon cls={cls} d="M7 4h10v16H7z|M9 8h6|M9 12h6|M9 16h4" />,
  },
  {
    key: "classify",
    label: "classify",
    hint: "Signal? category + priority",
    icon: (cls) =>
      <Icon cls={cls} d="M3 7l9-4 9 4-9 4-9-4z|M3 12l9 4 9-4|M3 17l9 4 9-4" />,
  },
  {
    key: "resolve",
    label: "resolve",
    hint: "Link entities from stammdaten",
    icon: (cls) =>
      <Icon cls={cls} d="M10 14a4 4 0 010-5.66l3-3a4 4 0 015.66 5.66l-1.5 1.5|M14 10a4 4 0 010 5.66l-3 3a4 4 0 01-5.66-5.66l1.5-1.5" />,
  },
  {
    key: "locate",
    label: "locate",
    hint: "Vector search wiki sections",
    icon: (cls) =>
      <Icon cls={cls} d="M12 2v3|M12 19v3|M2 12h3|M19 12h3|M12 7a5 5 0 100 10 5 5 0 000-10z|M12 12h.01" />,
  },
  {
    key: "extract",
    label: "extract",
    hint: "LLM → patch plan ops",
    icon: (cls) =>
      <Icon cls={cls} d="M4 4l8 8|M4 20l8-8|M14 7l6 5-6 5|M14 7v10" />,
  },
  {
    key: "patch",
    label: "patch",
    hint: "Apply ops to wiki files",
    icon: (cls) =>
      <Icon cls={cls} d="M12 20h9|M16.5 3.5a2.12 2.12 0 113 3L7 19l-4 1 1-4 12.5-12.5z" />,
  },
  {
    key: "index",
    label: "index",
    hint: "Regenerate property index.md",
    icon: (cls) =>
      <Icon cls={cls} d="M4 6h16|M4 12h16|M4 18h10|M20 18h.01" />,
  },
  {
    key: "reindex",
    label: "reindex",
    hint: "Refresh wiki vector chunks",
    icon: (cls) =>
      <Icon cls={cls} d="M21 12a9 9 0 11-3-6.7|M21 4v5h-5" />,
  },
];

type StageRecord = {
  state: StageState;
  data: Record<string, unknown> | null;
  startedAt: number | null;
  endedAt: number | null;
};

function emptyStages(): Record<string, StageRecord> {
  const out: Record<string, StageRecord> = {};
  for (const n of PIPELINE) {
    out[n.key] = { state: "pending", data: null, startedAt: null, endedAt: null };
  }
  return out;
}

const KIND_LABELS: Record<Kind, string> = {
  email: "Emails",
  invoice: "Invoices",
  bank: "Bank tx",
};

export function IngestPage() {
  const [days, setDays] = useState<SimDay[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [day, setDay] = useState<number | null>(null);
  const [kind, setKind] = useState<Kind>("email");
  const [itemId, setItemId] = useState<string | null>(null);
  const [mode, setMode] = useState<Mode>("isolated");
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<SimIngestResponse | null>(null);
  const [activeFile, setActiveFile] = useState<string | null>(null);
  const [events, setEvents] = useState<SimStageEvent[]>([]);
  const [cursor, setCursor] = useState<number>(-1);
  const [followLive, setFollowLive] = useState(true);

  useEffect(() => {
    fetchIncremental()
      .then((d) => {
        setDays(d);
        if (d.length > 0) setDay(d[d.length - 1].day);
      })
      .catch((e) => setError(String(e)));
  }, []);

  const currentDay = useMemo(
    () => days?.find((d) => d.day === day) ?? null,
    [days, day],
  );

  const items: SimItem[] = useMemo(() => {
    if (!currentDay) return [];
    if (kind === "email") return currentDay.emails;
    if (kind === "invoice") return currentDay.invoices;
    return currentDay.bank;
  }, [currentDay, kind]);

  useEffect(() => {
    if (items.length === 0) {
      setItemId(null);
      return;
    }
    if (!itemId || !items.some((i) => i.id === itemId)) {
      setItemId(items[0].id);
    }
  }, [items, itemId]);

  useEffect(() => {
    if (!result) {
      setActiveFile(null);
      return;
    }
    setActiveFile(result.files[0]?.path ?? null);
  }, [result]);

  function handleStage(ev: SimStageEvent) {
    setEvents((prev) => {
      const enriched: SimStageEvent = {
        ...ev,
        data: { ...ev.data, _recvAt: performance.now() },
      };
      const next = [...prev, enriched];
      if (followLive) setCursor(next.length - 1);
      return next;
    });
  }

  async function handleRun() {
    if (!day || !itemId) return;
    setRunning(true);
    setError(null);
    setResult(null);
    setEvents([]);
    setCursor(-1);
    setFollowLive(true);
    try {
      await runSimIngestStream(
        { day, kind, id: itemId, mode },
        {
          onStage: handleStage,
          onResponse: (resp) => setResult(resp),
          onError: (err) => setError(`${err.status}: ${err.detail}`),
        },
      );
    } catch (e) {
      setError(String(e));
    } finally {
      setRunning(false);
    }
  }

  const activeContent =
    result?.files.find((f) => f.path === activeFile)?.content ?? "";

  return (
    <div className="flex h-screen flex-col bg-[var(--color-bg)] text-[var(--color-fg)]">
      <header className="glass flex h-12 shrink-0 items-center gap-3 border-b border-[var(--color-border)] px-4">
        <a
          href="/"
          className="font-display text-[12px] font-medium text-[var(--color-ink-50)] hover:text-[var(--color-accent)]"
        >
          ← Buena Wiki
        </a>
        <span className="text-[12.5px] uppercase tracking-[0.18em] text-[var(--color-fg-muted)]">
          Simulate ingest
        </span>
      </header>

      <div className="flex min-h-0 flex-1">
        <aside className="flex w-[360px] shrink-0 flex-col border-r border-[var(--color-border)] bg-[var(--color-bg)]/40">
          <div className="border-b border-[var(--color-border)] px-3 py-3">
            <Field label="Day">
              <select
                value={day ?? ""}
                onChange={(e) => setDay(Number(e.target.value))}
                disabled={!days || days.length === 0}
                className="h-7 w-full appearance-none rounded-md border border-[var(--color-border-2)] bg-[var(--color-surface)] px-2 font-mono text-[13.5px] text-[var(--color-fg)]"
              >
                {(days ?? []).map((d) => (
                  <option key={d.day} value={d.day}>
                    day-{String(d.day).padStart(2, "0")}
                    {d.content_date ? `  ·  ${d.content_date}` : ""}
                  </option>
                ))}
              </select>
            </Field>
            <div className="mt-2 flex gap-1">
              {(Object.keys(KIND_LABELS) as Kind[]).map((k) => (
                <button
                  key={k}
                  onClick={() => setKind(k)}
                  className={cn(
                    "flex-1 rounded-md border px-2 py-1 font-mono text-[12.5px] uppercase tracking-wide transition-colors",
                    kind === k
                      ? "border-[var(--color-accent-dim)] bg-[var(--color-surface)] text-[var(--color-accent)]"
                      : "border-[var(--color-border-2)] bg-[var(--color-bg)] text-[var(--color-fg-muted)] hover:text-[var(--color-fg)]",
                  )}
                >
                  {KIND_LABELS[k]} ({currentDay ? currentDay[k === "bank" ? "bank" : k === "invoice" ? "invoices" : "emails"].length : 0})
                </button>
              ))}
            </div>
          </div>

          <div className="min-h-0 flex-1 overflow-auto px-1.5 py-2">
            {items.length === 0 ? (
              <p className="px-3 py-6 text-center text-[13.5px] text-[var(--color-fg-muted)]">
                No items.
              </p>
            ) : (
              items.map((it) => (
                <button
                  key={it.id}
                  onClick={() => setItemId(it.id)}
                  className={cn(
                    "mb-1 block w-full rounded-md border px-2.5 py-2 text-left transition-colors",
                    itemId === it.id
                      ? "border-[var(--color-accent-dim)] bg-[var(--color-surface)]"
                      : "border-transparent hover:border-[var(--color-border-2)] hover:bg-[var(--color-surface)]/60",
                  )}
                >
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-[12px] text-[var(--color-accent)]">
                      {it.id}
                    </span>
                  </div>
                  <div className="mt-0.5 line-clamp-1 text-[14.5px] font-medium text-[var(--color-fg)]">
                    {it.label}
                  </div>
                  <div className="mt-0.5 line-clamp-2 text-[12.5px] text-[var(--color-fg-muted)]">
                    {it.detail}
                  </div>
                </button>
              ))
            )}
          </div>

          <div className="border-t border-[var(--color-border)] px-3 py-3">
            <Field label="Mode">
              <div className="flex gap-1">
                {(["isolated", "live"] as Mode[]).map((m) => (
                  <button
                    key={m}
                    onClick={() => setMode(m)}
                    className={cn(
                      "flex-1 rounded-md border px-2 py-1 font-mono text-[12.5px] transition-colors",
                      mode === m
                        ? "border-[var(--color-accent-dim)] bg-[var(--color-surface)] text-[var(--color-accent)]"
                        : "border-[var(--color-border-2)] bg-[var(--color-bg)] text-[var(--color-fg-muted)] hover:text-[var(--color-fg)]",
                    )}
                  >
                    {m}
                  </button>
                ))}
              </div>
              <p className="mt-1 text-[12px] text-[var(--color-fg-muted)]">
                {mode === "isolated"
                  ? "Fresh tmp wiki per run. Real Gemini, no live mutation."
                  : "Writes to wiki/LIE-001 + commits."}
              </p>
            </Field>
            <button
              onClick={handleRun}
              disabled={!itemId || running}
              className={cn(
                "mt-3 w-full rounded-md border px-3 py-2 font-mono text-[13.5px] font-medium transition-colors",
                running
                  ? "border-[var(--color-border-2)] bg-[var(--color-surface)] text-[var(--color-fg-muted)]"
                  : "border-[var(--color-accent)] bg-[var(--color-accent)] text-[#0b0b0a] hover:opacity-90",
                !itemId && "cursor-not-allowed opacity-50",
              )}
            >
              {running ? "Running…" : `▶ Run ingest (${itemId ?? "—"})`}
            </button>
          </div>
        </aside>

        <main className="flex min-w-0 flex-1 flex-col">
          {error && (
            <div className="border-b border-red-500/40 bg-red-500/10 px-4 py-2 text-[13.5px] text-red-400">
              {error}
            </div>
          )}
          {!result && !running && !error && (
            <div className="grid flex-1 place-items-center text-[14.5px] text-[var(--color-fg-muted)]">
              Pick a day + item, then run. Uses real Gemini ({"gemini-2.5-flash-lite"} → {"gemini-2.5-pro"}).
            </div>
          )}
          {(running || events.length > 0) && (
            <PipelineView
              events={events}
              cursor={cursor}
              followLive={followLive}
              running={running}
              onCursor={(idx) => {
                setCursor(idx);
                setFollowLive(idx === events.length - 1);
              }}
              onFollowLive={() => {
                setFollowLive(true);
                setCursor(events.length - 1);
              }}
            />
          )}
          {result && (
            <ResultView
              result={result}
              activeFile={activeFile}
              onActiveFile={setActiveFile}
              activeContent={activeContent}
            />
          )}
        </main>
      </div>
    </div>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <span className="block pb-1 font-mono text-[12px] uppercase tracking-[0.2em] text-[var(--color-fg-dim)]">
        {label}
      </span>
      {children}
    </label>
  );
}

function ResultView({
  result,
  activeFile,
  onActiveFile,
  activeContent,
}: {
  result: SimIngestResponse;
  activeFile: string | null;
  onActiveFile: (p: string) => void;
  activeContent: string;
}) {
  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="grid grid-cols-2 gap-x-6 gap-y-1 border-b border-[var(--color-border)] px-4 py-3 font-mono text-[13px]">
        <Stat label="status" value={result.status} accent />
        <Stat label="duration" value={`${result.duration_ms} ms`} />
        <Stat label="applied_ops" value={String(result.applied_ops)} />
        <Stat
          label="provider"
          value={`${result.provider} (${result.fast_model} → ${result.smart_model})`}
        />
        <Stat
          label="commit"
          value={result.commit_sha ? result.commit_sha.slice(0, 10) : "—"}
        />
        <Stat label="idempotent" value={String(result.idempotent)} />
        {result.classification && (
          <>
            <Stat
              label="classify.signal"
              value={String(result.classification.signal)}
              accent={result.classification.signal}
            />
            <Stat
              label="classify"
              value={`${result.classification.category}  ·  ${result.classification.priority}  ·  conf=${result.classification.confidence}`}
            />
          </>
        )}
        <Stat label="workspace" value={result.workspace} colSpan={2} mono />
      </div>

      <div className="flex min-h-0 flex-1">
        <aside className="flex w-[260px] shrink-0 flex-col border-r border-[var(--color-border)]">
          <div className="border-b border-[var(--color-border)] px-3 py-2 font-mono text-[12px] uppercase tracking-[0.2em] text-[var(--color-fg-dim)]">
            Touched files ({result.files.length})
          </div>
          <div className="min-h-0 flex-1 overflow-auto px-1.5 py-1.5">
            {result.files.map((f) => (
              <button
                key={f.path}
                onClick={() => onActiveFile(f.path)}
                className={cn(
                  "block w-full truncate rounded px-2 py-1 text-left font-mono text-[13px]",
                  activeFile === f.path
                    ? "bg-[var(--color-surface)] text-[var(--color-accent)]"
                    : "text-[var(--color-fg-muted)] hover:bg-[var(--color-surface)]/60 hover:text-[var(--color-fg)]",
                )}
              >
                {f.path}
              </button>
            ))}
          </div>
          {result.git_log.length > 0 && (
            <div className="border-t border-[var(--color-border)] px-3 py-2">
              <div className="pb-1 font-mono text-[12px] uppercase tracking-[0.2em] text-[var(--color-fg-dim)]">
                git log
              </div>
              <ul className="space-y-0.5 font-mono text-[12px] text-[var(--color-fg-muted)]">
                {result.git_log.map((ln) => (
                  <li key={ln} className="truncate">
                    {ln}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </aside>

        <section className="prose min-w-0 flex-1 overflow-auto px-6 py-4 text-[15px] dark:prose-invert">
          {activeFile ? (
            <>
              <div className="mb-3 font-mono text-[12px] uppercase tracking-[0.2em] text-[var(--color-fg-dim)]">
                {activeFile}
              </div>
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {activeContent}
              </ReactMarkdown>
            </>
          ) : (
            <p className="text-[var(--color-fg-muted)]">No files touched.</p>
          )}
        </section>
      </div>
    </div>
  );
}

function Stat({
  label,
  value,
  accent,
  mono,
  colSpan,
}: {
  label: string;
  value: string;
  accent?: boolean;
  mono?: boolean;
  colSpan?: number;
}) {
  return (
    <div className={colSpan === 2 ? "col-span-2" : ""}>
      <span className="text-[var(--color-fg-dim)]">{label}</span>{" "}
      <span
        className={cn(
          accent && "text-[var(--color-accent)]",
          mono && "break-all",
        )}
      >
        {value}
      </span>
    </div>
  );
}

type DerivedView = {
  stages: Record<string, StageRecord>;
  activeStage: string | null;
  terminalStatus: "applied" | "no_signal" | null;
  currentEvent: SimStageEvent | null;
};

function deriveFromEvents(events: SimStageEvent[], upto: number): DerivedView {
  const stages = emptyStages();
  let activeStage: string | null = null;
  let terminalStatus: "applied" | "no_signal" | null = null;
  const slice = upto < 0 ? [] : events.slice(0, upto + 1);
  for (const ev of slice) {
    const raw = ev.stage;
    if (raw === "done") {
      terminalStatus = (ev.data?.status as "applied" | "no_signal") ?? null;
      activeStage = null;
      if (terminalStatus === "no_signal") {
        for (const n of PIPELINE) {
          if (
            n.key !== "normalize" &&
            n.key !== "classify" &&
            stages[n.key].state === "pending"
          ) {
            stages[n.key] = { ...stages[n.key], state: "skipped" };
          }
        }
      }
      continue;
    }
    const isDone = raw.endsWith(".done");
    const key = isDone ? raw.slice(0, -5) : raw;
    if (!PIPELINE.some((n) => n.key === key)) continue;
    const cur = stages[key];
    const { _recvAt, ...visibleData } = ev.data as Record<string, unknown>;
    const ts = typeof _recvAt === "number" ? _recvAt : null;
    if (isDone) {
      stages[key] = {
        ...cur,
        state: "done",
        data: visibleData,
        endedAt: ts,
      };
      if (activeStage === key) activeStage = null;
    } else {
      stages[key] = {
        ...cur,
        state: "active",
        startedAt: ts,
      };
      activeStage = key;
    }
  }
  const currentEvent = upto >= 0 && upto < events.length ? events[upto] : null;
  return { stages, activeStage, terminalStatus, currentEvent };
}

function PipelineView({
  events,
  cursor,
  followLive,
  running,
  onCursor,
  onFollowLive,
}: {
  events: SimStageEvent[];
  cursor: number;
  followLive: boolean;
  running: boolean;
  onCursor: (idx: number) => void;
  onFollowLive: () => void;
}) {
  const { stages, activeStage, terminalStatus, currentEvent } = useMemo(
    () => deriveFromEvents(events, cursor),
    [events, cursor],
  );
  const total = events.length;
  const idx = cursor < 0 ? 0 : cursor + 1;
  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="border-b border-[var(--color-border)] px-4 py-3">
        <div className="mb-2 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="font-mono text-[11px] uppercase tracking-[0.2em] text-[var(--color-fg-dim)]">
              Pipeline
            </span>
            {currentEvent && (
              <span className="font-mono text-[11px] text-[var(--color-fg-muted)]">
                · {currentEvent.stage}
              </span>
            )}
          </div>
          <span
            className={cn(
              "font-mono text-[11px] uppercase tracking-[0.18em]",
              terminalStatus === "applied" && "text-[var(--color-accent)]",
              terminalStatus === "no_signal" &&
                "text-[var(--color-fg-muted)]",
              !terminalStatus && running && "text-[var(--color-accent)]",
            )}
          >
            {terminalStatus
              ? terminalStatus.replace("_", " ")
              : running
                ? "running"
                : "idle"}
          </span>
        </div>
        <div className="flex flex-wrap items-stretch gap-1">
          {PIPELINE.map((node, i) => {
            const rec = stages[node.key];
            return (
              <div key={node.key} className="flex items-stretch">
                <StageChip
                  node={node}
                  state={rec.state}
                  active={activeStage === node.key}
                  data={rec.data}
                  duration={
                    rec.startedAt && rec.endedAt
                      ? rec.endedAt - rec.startedAt
                      : null
                  }
                  onClick={() => {
                    const target = lastEventIndexFor(events, node.key);
                    if (target >= 0) onCursor(target);
                  }}
                />
                {i < PIPELINE.length - 1 && <Connector />}
              </div>
            );
          })}
        </div>
        <div className="mt-3 flex items-center gap-2">
          <button
            onClick={() => onCursor(Math.max(0, cursor - 1))}
            disabled={cursor <= 0}
            className="rounded border border-[var(--color-border-2)] bg-[var(--color-bg)] px-2 py-1 font-mono text-[11px] text-[var(--color-fg-muted)] hover:text-[var(--color-fg)] disabled:opacity-30"
            title="prev event"
          >
            ◀ prev
          </button>
          <input
            type="range"
            min={0}
            max={Math.max(0, total - 1)}
            value={cursor < 0 ? 0 : cursor}
            disabled={total === 0}
            onChange={(e) => onCursor(Number(e.target.value))}
            className="flex-1 accent-[var(--color-accent)]"
          />
          <button
            onClick={() => onCursor(Math.min(total - 1, cursor + 1))}
            disabled={cursor >= total - 1 || total === 0}
            className="rounded border border-[var(--color-border-2)] bg-[var(--color-bg)] px-2 py-1 font-mono text-[11px] text-[var(--color-fg-muted)] hover:text-[var(--color-fg)] disabled:opacity-30"
            title="next event"
          >
            next ▶
          </button>
          <button
            onClick={onFollowLive}
            disabled={followLive || total === 0}
            className={cn(
              "rounded border px-2 py-1 font-mono text-[11px] uppercase tracking-wide transition-colors",
              followLive
                ? "border-[var(--color-accent-dim)] bg-[var(--color-surface)] text-[var(--color-accent)]"
                : "border-[var(--color-border-2)] bg-[var(--color-bg)] text-[var(--color-fg-muted)] hover:text-[var(--color-fg)]",
            )}
            title="snap to latest event"
          >
            live
          </button>
          <span className="ml-1 font-mono text-[11px] text-[var(--color-fg-muted)]">
            {idx} / {total}
          </span>
        </div>
        {currentEvent && (
          <div className="mt-2 font-mono text-[11px] text-[var(--color-fg-muted)]">
            {hintFor(currentEvent.stage)}
          </div>
        )}
      </div>
      <div className="grid grid-cols-2 gap-3 overflow-auto px-4 py-3">
        {PIPELINE.filter((n) => stages[n.key].data || stages[n.key].state === "active").map(
          (n) => (
            <StagePanel key={n.key} node={n} record={stages[n.key]} />
          ),
        )}
        {Object.values(stages).every(
          (s) => s.state === "pending" || s.state === "active",
        ) &&
          running && (
            <div className="col-span-2 text-[12.5px] text-[var(--color-fg-muted)]">
              waiting for first stage…
            </div>
          )}
      </div>
    </div>
  );
}

function lastEventIndexFor(events: SimStageEvent[], key: string): number {
  for (let i = events.length - 1; i >= 0; i--) {
    const raw = events[i].stage;
    const k = raw.endsWith(".done") ? raw.slice(0, -5) : raw;
    if (k === key) return i;
  }
  return -1;
}

function hintFor(stage: string): string {
  if (stage === "done") return "Pipeline finished.";
  const isDone = stage.endsWith(".done");
  const key = isDone ? stage.slice(0, -5) : stage;
  const node = PIPELINE.find((n) => n.key === key);
  if (!node) return stage;
  return isDone ? `${node.label} → done. ${node.hint}` : `${node.label} → ${node.hint}`;
}

function StageChip({
  node,
  state,
  active,
  data,
  duration,
  onClick,
}: {
  node: StageNode;
  state: StageState;
  active: boolean;
  data: Record<string, unknown> | null;
  duration: number | null;
  onClick: () => void;
}) {
  const bgClass =
    state === "done"
      ? "border-[var(--color-accent-dim)] bg-[var(--color-surface)] text-[var(--color-accent)]"
      : state === "active" || active
        ? "border-[var(--color-accent)] bg-[var(--color-accent)]/15 text-[var(--color-accent)] animate-pulse"
        : state === "error"
          ? "border-red-500/50 bg-red-500/10 text-red-400"
          : state === "skipped"
            ? "border-[var(--color-border-2)] bg-[var(--color-bg)] text-[var(--color-fg-dim)] opacity-60"
            : "border-[var(--color-border-2)] bg-[var(--color-bg)] text-[var(--color-fg-muted)]";
  const indicator =
    state === "done"
      ? "✓"
      : state === "active" || active
        ? "●"
        : state === "error"
          ? "✕"
          : state === "skipped"
            ? "—"
            : "○";
  const summary = chipSummary(node.label, data);
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex min-w-[120px] flex-col rounded-md border px-2 py-1.5 text-left font-mono text-[11px] transition-colors hover:brightness-110",
        bgClass,
      )}
      title={`${node.hint}${data ? `\n\n${JSON.stringify(data, null, 2)}` : ""}`}
    >
      <div className="flex items-center gap-1.5">
        <span className="text-[10px]">{indicator}</span>
        {node.icon()}
        <span className="font-medium uppercase tracking-wide">{node.label}</span>
      </div>
      {summary && (
        <span className="mt-0.5 truncate text-[10.5px] opacity-80">
          {summary}
        </span>
      )}
      {duration !== null && (
        <span className="text-[9.5px] opacity-60">{Math.round(duration)}ms</span>
      )}
    </button>
  );
}

function Connector() {
  return (
    <div className="flex items-center px-0.5 text-[var(--color-border-2)]">
      <span className="font-mono text-[12px]">→</span>
    </div>
  );
}

function chipSummary(
  label: string,
  data: Record<string, unknown> | null,
): string | null {
  if (!data) return null;
  if (label === "classify") {
    const cat = data.category as string | undefined;
    const conf = data.confidence as number | undefined;
    if (cat) return `${cat} ${conf != null ? `· ${conf}` : ""}`.trim();
  }
  if (label === "extract") {
    const ops = data.ops as number | undefined;
    if (typeof ops === "number") return `${ops} ops`;
  }
  if (label === "patch") {
    const ops = data.applied_ops as number | undefined;
    if (typeof ops === "number") return `${ops} writes`;
  }
  if (label === "resolve") {
    const ids = data.entity_ids as string[] | undefined;
    if (ids && ids.length) return ids.slice(0, 2).join(", ");
  }
  if (label === "locate") {
    const sec = data.sections as string[] | undefined;
    if (sec && sec.length) return `${sec.length} sections`;
  }
  if (label === "normalize") {
    const chars = data.chars as number | undefined;
    if (typeof chars === "number") return `${chars} chars`;
  }
  if (label === "reindex") {
    const c = data.count as number | undefined;
    if (typeof c === "number") return `${c} files`;
  }
  return null;
}

function StagePanel({
  node,
  record,
}: {
  node: StageNode;
  record: StageRecord;
}) {
  if (!record.data && record.state !== "active") return null;
  return (
    <div className="rounded-md border border-[var(--color-border-2)] bg-[var(--color-surface)]/40 p-2">
      <div className="mb-1 flex items-center justify-between font-mono text-[11px] uppercase tracking-[0.18em] text-[var(--color-fg-dim)]">
        <span className="flex items-center gap-1.5">
          {node.icon()}
          {node.label}
        </span>
        <span
          className={cn(
            record.state === "done" && "text-[var(--color-accent)]",
            record.state === "active" && "text-[var(--color-accent)]",
          )}
        >
          {record.state}
        </span>
      </div>
      {record.data ? (
        <pre className="max-h-[220px] overflow-auto whitespace-pre-wrap break-all font-mono text-[11px] leading-snug text-[var(--color-fg-muted)]">
          {JSON.stringify(record.data, null, 2)}
        </pre>
      ) : (
        <div className="font-mono text-[11px] text-[var(--color-fg-muted)]">
          working…
        </div>
      )}
    </div>
  );
}
