# Chat Agent Schema

## Purpose

Answer property-management questions from the compiled `context.md` artifact without editing files.

## Agent Boundary

- The chat agent may read `context.md`.
- The chat agent may retrieve relevant sections.
- The chat agent may call the configured language model for synthesis.
- The chat agent may use deterministic synthesis when the model is unavailable.
- The chat agent must not write to `context.md`.
- The chat agent must not stage resources.
- The chat agent must not change patches, schemas, outputs, or source data.

## Required Steps

1. Validate the question is non-empty.
2. Load the compiled context artifact.
3. Retrieve the strongest evidence sections.
4. Build a short answer plan containing:
   - detected intent
   - retrieval strategy
   - safety constraints
5. Synthesize a human-readable answer.
6. Return evidence titles and mode metadata for the UI.

## Intent Hints

- Financial risk: risk, anomaly, review, unresolved, financial, unpaid, payment, invoice.
- Owner lookup: owner, owns, unit, WE, EH, EIG.
- Service provider lookup: provider, vendor, contractor, service, dienstleister.
- Operational topic: topic, open, issue, maintenance, heating, water, damage.
- General context: any other valid property-management question.

## Answer Rules

- Prefer plain natural language.
- Mention uncertainty when the compiled context does not contain enough evidence.
- Do not invent property facts.
- Do not expose raw JSON unless the user explicitly asks for technical output.
- Keep answers concise enough for a chat panel.
- If the model fails, continue with deterministic synthesis and include a short safe note.
