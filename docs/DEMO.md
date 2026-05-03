# Demo Script

Use this flow for a short face-video demo.

## 1. Open The App

Open:

```text
http://127.0.0.1:3000
```

Say:

> This is the Buena Context Engine. It turns scattered property-management records into one living context artifact.

## 2. Ask A Question

Ask:

```text
Who owns WE 01?
```

Show:

- The answer appears in natural language.
- The trace includes `route_building`, `search_context`, `model_synthesis`, and `citations`.
- `model_synthesis` means Claude synthesized the final answer from retrieved evidence.

## 3. Ask A Prioritization Question

Ask:

```text
What should a property manager review first today?
```

Say:

> The model is not answering from memory. The deterministic retrieval step first finds evidence in context.md, then the AI summarizes from that evidence.

## 4. Write Into Context From Chat

Ask:

```text
Add note: Heating contractor confirmed a follow-up appointment for 2026-04-27.
```

Show:

- The artifact switches to `context.md`.
- The inserted note is highlighted.
- The trace shows the write path.

## 5. Add A Resource

Click the resource icon in the top-right chrome.

Paste:

```text
Subject: Maintenance update
Vendor confirms the stairwell light repair appointment for next week.
```

Click preview.

Show:

- The app validates the resource.
- A side-by-side diff appears.
- Nothing writes until the user approves.

Then click apply.

## 6. Manual Edit Protection

Open the artifact edit icon.

Change one line, then save.

Show:

- The edit is wrapped in `<user>...</user>` tags.
- Explain that future ingestion and AI writes are blocked if they try to modify protected user blocks.

## 7. Mechanism Page

Open:

```text
http://127.0.0.1:3000/mechanism
```

Say:

> This page explains the full system: read flow, write flow, resource intake, rollback, and safety gates.

## One-Sentence Pitch

Buena Context Engine gives property managers a living memory for each building: searchable, editable, AI-assisted, and protected by deterministic safety gates.
