import { useEffect, useRef, useState } from "react";
import { Pencil, Check, X, Loader2 } from "lucide-react";
import { saveHumanNotes } from "../api";

type Props = {
  path: string;
  initialBody: string;
  pmUser: string;
  onSaved: (newBody: string) => void;
};

export function HumanNotesEditor({
  path,
  initialBody,
  pmUser,
  onSaved,
}: Props) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(initialBody);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    setDraft(initialBody);
    setError(null);
    setEditing(false);
  }, [path, initialBody]);

  useEffect(() => {
    if (editing && textareaRef.current) {
      textareaRef.current.focus();
      const len = textareaRef.current.value.length;
      textareaRef.current.setSelectionRange(len, len);
    }
  }, [editing]);

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      await saveHumanNotes(path, draft, pmUser);
      onSaved(draft);
      setEditing(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  }

  function handleCancel() {
    setDraft(initialBody);
    setError(null);
    setEditing(false);
  }

  return (
    <section className="mt-10 border-t border-[var(--color-border)] pt-6">
      <header className="mb-3 flex items-center justify-between">
        <div>
          <h1 className="font-display text-[20px] font-medium tracking-tight text-[var(--color-ink-50)]">
            Human Notes
          </h1>
          <p className="mt-0.5 font-mono text-[10.5px] uppercase tracking-[0.18em] text-[var(--color-fg-dim)]">
            sacred · agent never writes here
          </p>
        </div>
        {!editing && (
          <button
            onClick={() => setEditing(true)}
            className="inline-flex items-center gap-1.5 rounded-md border border-[var(--color-border-2)] bg-[var(--color-surface)] px-2.5 py-1 font-mono text-[11px] text-[var(--color-fg)] transition-colors hover:border-[var(--color-accent-dim)] hover:text-[var(--color-accent)]"
          >
            <Pencil className="h-3 w-3" />
            Edit
          </button>
        )}
      </header>

      {editing ? (
        <div className="space-y-2">
          <textarea
            ref={textareaRef}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            disabled={saving}
            className="w-full min-h-[180px] resize-y rounded-md border border-[var(--color-border-2)] bg-[var(--color-surface)] px-3 py-2 font-mono text-[12.5px] leading-relaxed text-[var(--color-fg)] outline-none focus:border-[var(--color-accent)]"
            placeholder="Write notes here. Markdown supported. Agent will never overwrite."
          />
          <div className="flex items-center justify-between">
            <span className="font-mono text-[10.5px] text-[var(--color-fg-dim)]">
              {draft.length} chars · committed as {pmUser}
            </span>
            <div className="flex gap-2">
              <button
                onClick={handleCancel}
                disabled={saving}
                className="inline-flex items-center gap-1.5 rounded-md border border-[var(--color-border-2)] bg-[var(--color-surface)] px-2.5 py-1 font-mono text-[11px] text-[var(--color-fg-muted)] transition-colors hover:text-[var(--color-fg)] disabled:opacity-40"
              >
                <X className="h-3 w-3" />
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={saving || draft === initialBody}
                className="inline-flex items-center gap-1.5 rounded-md border border-[var(--color-accent-dim)] bg-[var(--color-accent)]/10 px-2.5 py-1 font-mono text-[11px] text-[var(--color-accent)] transition-colors hover:bg-[var(--color-accent)]/20 disabled:opacity-40"
              >
                {saving ? (
                  <Loader2 className="h-3 w-3 animate-spin" />
                ) : (
                  <Check className="h-3 w-3" />
                )}
                Save
              </button>
            </div>
          </div>
          {error && (
            <div className="rounded border border-red-500/30 bg-red-500/5 px-3 py-2 font-mono text-[11px] text-red-300">
              {error}
            </div>
          )}
        </div>
      ) : (
        <pre className="whitespace-pre-wrap rounded-md border border-[var(--color-border)] bg-[var(--color-surface)]/40 p-4 font-mono text-[12.5px] leading-relaxed text-[var(--color-fg)]">
          {initialBody || (
            <span className="italic text-[var(--color-fg-dim)]">
              No notes yet. Click Edit to add.
            </span>
          )}
        </pre>
      )}
    </section>
  );
}
