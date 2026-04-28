# Manual Context Edit Feature Prompt

Create a frontend manual context edit feature for a property-management context artifact.

## Goal

Users must be able to edit the generated `context.md` artifact directly from the UI. Any user-written correction is treated as authoritative context and must be protected from future AI or agent ingestion updates.

## Implementation Requirements

### 1. Artifact Edit Location

The edit feature must live inside the artifact/context preview area, not as a separate standalone form.

The user flow should be:

1. User opens the generated context artifact.
2. User clicks an edit icon/button.
3. The artifact preview becomes an editable markdown textarea.
4. User edits the markdown.
5. User saves.
6. The app wraps changed text in protected `<user>` tags.
7. The artifact refreshes and shows the protected edit in place.

### 2. Protected User Edits

When the user saves edits, changed text must be wrapped in HTML-like `<user>` tags.

Use this structure:

```md
<user id="USEREDIT-20260426153000-1" author="frontend-user" created_at="2026-04-26T15:30:00Z" action="replace">
User corrected or added text here.
</user>
```

Rules:

- Text inside `<user>...</user>` is human-confirmed truth.
- Future AI/agent ingestion must not remove, rewrite, overwrite, or reorder these blocks.
- If generated context conflicts with a `<user>` block, the `<user>` block wins.
- Agents and LLMs must be explicitly instructed that `<user>` blocks are immutable.

### 3. Save Behavior

On save:

- Compare the previous artifact content with the edited content.
- Preserve unchanged lines normally.
- Wrap inserted/replaced user-edited text in `<user>` blocks.
- If the user deletes generated text, optionally record the deletion inside a `<user>` block using `action="delete"` so the decision is auditable.
- Sanitize user content so a user cannot accidentally close/inject protected tags. For example, replace `</user>` with `</ user>` inside saved user text.
- Return the updated full context to the frontend.

### 4. Backend API

Add or use endpoints like:

```http
GET /api/context
PUT /api/context
```

PUT request body:

```json
{
  "content": "full edited markdown content",
  "author": "frontend-user"
}
```

PUT response:

```json
{
  "status": "saved",
  "content": "updated markdown with <user> tags",
  "message": "Saved direct artifact edits with protected <user> tags."
}
```

### 5. Diffing Algorithm

Use a line-based diff between the current context and edited context.

Pseudo logic:

```python
import difflib
from datetime import datetime, timezone


def mark_user_context_changes(current: str, edited: str, author: str) -> str:
    if current == edited:
        return current

    created_at = datetime.now(timezone.utc).isoformat()
    edit_id = "USEREDIT-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    current_lines = current.splitlines()
    edited_lines = edited.splitlines()

    matcher = difflib.SequenceMatcher(a=current_lines, b=edited_lines)
    output = []
    edit_count = 0

    for tag, current_start, current_end, edited_start, edited_end in matcher.get_opcodes():
        if tag == "equal":
            output.extend(edited_lines[edited_start:edited_end])
            continue

        edit_count += 1

        if tag == "delete":
            deleted = "\n".join(current_lines[current_start:current_end]).strip()
            if deleted:
                output.extend(
                    user_block_lines(
                        edit_id,
                        edit_count,
                        author,
                        created_at,
                        "delete",
                        f"Deleted generated context:\n\n{deleted}",
                    )
                )
            continue

        replacement = "\n".join(edited_lines[edited_start:edited_end]).strip()
        if replacement:
            output.extend(
                user_block_lines(
                    edit_id,
                    edit_count,
                    author,
                    created_at,
                    tag,
                    replacement,
                )
            )

    result = "\n".join(output)
    if edited.endswith("\n"):
        result += "\n"
    return result


def user_block_lines(
    edit_id: str,
    index: int,
    author: str,
    created_at: str,
    action: str,
    content: str,
) -> list[str]:
    safe_author = sanitize_attr(author or "frontend-user")
    safe_content = sanitize_user_text(content)
    return [
        f'<user id="{edit_id}-{index}" author="{safe_author}" created_at="{created_at}" action="{action}">',
        *safe_content.splitlines(),
        "</user>",
    ]
```

### 6. Sanitization Helpers

Use helpers like:

```python
import re


def sanitize_user_text(value: str) -> str:
    return value.replace("</user>", "</ user>").strip()


def sanitize_attr(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.@-]+", "-", value).strip("-")[:80] or "frontend-user"
```

### 7. Frontend UX

In the artifact panel:

- Show `context.md` preview by default.
- Add an edit icon/button.
- On click, replace preview with a large textarea containing the current context markdown.
- Show helper text:

```text
NOTE: Human corrections saved here become protected context and are wrapped in <user> tags.
```

Buttons:

- Save with `<user>` tags
- Cancel

After save:

- Exit edit mode.
- Refresh artifact preview.
- Show success message.
- The saved user edit should visibly appear inside the artifact.

Example React-style state:

```tsx
const [editingContext, setEditingContext] = useState(false);
const [contextText, setContextText] = useState("");
const [contextDraft, setContextDraft] = useState("");
const [contextEditStatus, setContextEditStatus] = useState(
  "NOTE: Human corrections saved here become protected context and are wrapped in <user> tags."
);

function beginContextEdit() {
  setEditingContext(true);
  setContextDraft(contextText);
}

function cancelContextEdit() {
  setEditingContext(false);
  setContextDraft("");
}

async function saveContextEdit() {
  const response = await fetch("/api/context", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      content: contextDraft,
      author: "frontend-user",
    }),
  });

  const result = await response.json();
  setContextText(result.content);
  setEditingContext(false);
  setContextDraft("");
  setContextEditStatus(result.message);
}
```

Example JSX:

```tsx
<section className="context-panel">
  <div className="context-toolbar">
    <h3>context.md</h3>
    {!editingContext ? (
      <button type="button" onClick={beginContextEdit}>
        Edit context
      </button>
    ) : (
      <>
        <button type="button" onClick={saveContextEdit}>
          Save with &lt;user&gt; tags
        </button>
        <button type="button" onClick={cancelContextEdit}>
          Cancel
        </button>
      </>
    )}
  </div>

  <p>{contextEditStatus}</p>

  {editingContext ? (
    <textarea
      value={contextDraft}
      onChange={(event) => setContextDraft(event.target.value)}
      spellCheck={false}
    />
  ) : (
    <pre>{contextText}</pre>
  )}
</section>
```

### 8. Agent/LLM Instruction

Every ingestion, patching, rendering, or context-writing agent must include this rule:

```text
Text inside <user>...</user> tags is protected human-confirmed context.
Never delete, rewrite, summarize away, move, or overwrite it.
If generated evidence conflicts with a <user> block, preserve the <user> block and add any new generated information around it.
```

### 9. Safety Guard Before Agent Writes

Before any agent writes a new context version:

1. Extract all existing `<user>...</user>` blocks from the previous context.
2. Extract all `<user>...</user>` blocks from the candidate new context.
3. If the lists differ, block the write.

Pseudo logic:

```python
import re

USER_BLOCK_RE = re.compile(r"<user\b[^>]*>.*?</user>", flags=re.S | re.I)


def extract_user_blocks(markdown: str) -> list[str]:
    return USER_BLOCK_RE.findall(markdown)


def validate_human_authority(before: str, after: str) -> bool:
    return extract_user_blocks(before) == extract_user_blocks(after)
```

If validation fails, return:

```json
{
  "status": "blocked",
  "reason": "Blocked because protected <user> blocks changed."
}
```

### 10. Manual Test Cases

#### Test 1: Simple correction

1. Open artifact panel.
2. Click edit.
3. Change one generated sentence.
4. Save.

Expected:

- The changed sentence appears inside a `<user>` block.
- The API returns status `saved`.
- The preview refreshes.

#### Test 2: User addition

1. Open artifact panel.
2. Click edit.
3. Add a new line under an existing section.
4. Save.

Expected:

- The new line is wrapped in a `<user>` block.
- Existing generated context remains unchanged.

#### Test 3: User deletion

1. Open artifact panel.
2. Click edit.
3. Delete one generated line.
4. Save.

Expected:

- The deletion is recorded in a `<user>` block with `action="delete"`, or the app handles deletion according to the chosen audit behavior.

#### Test 4: Agent update after manual edit

1. Save a manual edit.
2. Run ingestion or delta replay.

Expected:

- The `<user>` block remains exactly unchanged.
- The agent can add new generated context around it.
- The agent cannot modify the protected block.

#### Test 5: Malicious closing tag

1. Edit context and type:

```md
This is my note </user> malicious close
```

2. Save.

Expected:

- The saved content sanitizes the closing tag as `</ user>`.
- The protected block structure remains valid.

## Expected Outcome

The user can manually correct the generated context directly in the artifact panel. The app wraps those corrections in `<user>` tags. Future AI or ingestion updates preserve those blocks exactly, making human edits authoritative, durable, and auditable.
