# BerlinHack × Buena — Pitch Background Brief

## The Challenge (Buena)
Build an engine that produces a single Context Markdown File per property — a living, self-updating document containing every fact an AI agent needs to act. Dense, structured, traced to its source, surgically updated without destroying human edits.

## The Core Problem
Property management context is scattered: ERP systems, Gmail, Slack, Google Drive, scanned PDFs, bank statements, and the head of the property manager who has been there twelve years. AI agents must crawl all of it from scratch on every single task. There is no accumulation. There is no institutional memory.

## Our Solution Name
**BaC (Building as Context) — Hermes Wiki Engine**

## What We Built (Three-Layer Architecture)

### Layer 1: Ingestion Pipeline
Raw sources (emails, invoices, letters, bank transactions) → Normalize → Classify (90% of emails are noise, filtered by Haiku) → Extract → Surgical Patcher → single `building.md` per property (called `LIE-001/index.md` in German WEG law terms).

Surgical updates: patches happen at the bullet/row level. A new email touching one issue changes exactly 4 lines across 3 files. Human edits are never overwritten. Every fact is traced to its source via footnotes.

### Layer 2: Living Context File Structure
One `building.md` (Liegenschaft index) is the entry point. It links to sub-files:
- Building status and health score
- Open issues with emoji-coded priority (🔴🟡🟢)
- Recent events ring buffer (max 50)
- Owners, tenants, service providers (entity pages)
- Finances and reconciliation
- **Procedural Memory** — the key section that grows via Hermes

### Layer 3: Hermes Self-Improvement (THE MOAT)
Two loops run asynchronously after each ingest commit:

**Inner Loop — Skill Extraction**
- Trigger: complexity_score > 5 (= num_tool_calls + 2×docs + prose_merges)
- Action: Linter replays the task trajectory, distills a procedural skill
- Output: new `@skill` entry in `06_skills.md` + one-line bullet in `## Procedural Memory`
- Example: after 2 heating emergencies resolved correctly, it writes: "heating-emergency-after-hours: call DL-007 (Notdienst), NOT DL-003 (Hausmeister has no key). Confidence: 0.92"
- The procedural memory grows. Future agents find the right answer in the context file.

**Outer Loop — Schema Mutation**
- Trigger: any (file, section) pair accumulates failure_score ≥ 3 in rolling 30 ingests
  - failure_score = 1×(retrieval miss) + 2×(PM correction) + 1×(missing_context)
- Action: Linter proposes a minimal schema change (add section, split section, add bullet convention)
- Gate: PM reviews and approves in `_pending_review.md` (one-click)
- Output: schema itself mutates, all affected building files patched, schema_version bumped
- Example: agent repeatedly fails to find contractor phone numbers → outer loop proposes adding `📞 **{DL-id}:** {phone}` bullet convention to Contractors section → approved → applied to all 3 buildings
- The schema learns what it needs to know.

## Feedback Substrate
All loops are grounded in `_hermes_feedback.jsonl` — an append-only JSONL event log per property. DuckDB-queryable. Tracks: ingest outcomes, retrieval success/failure, skill extractions, corrections, schema proposals and approvals.

## The Key Differentiator vs. Competition

| System | What grows | What stays fixed |
|---|---|---|
| RAG (ChatGPT, NotebookLM) | — | Everything, re-derived every query |
| Karpathy LLM Wiki | Wiki content | Schema defined upfront by humans |
| **Hermes Wiki Engine** | Wiki content + Procedural Memory | Nothing — schema evolves under empirical pressure |

Quote from architecture doc: "Karpathy's `llm-wiki` has only the inner loop. Buena's moat = the outer."

## The Compound Effect
- Day 1: Generic schema, empty procedural memory
- Month 3: Knows which contractor to call for which emergency. Auto-drafts routine letters.
- Month 12: Schema has evolved sections nobody thought to design upfront. Institutional memory outlasts any individual property manager.

## Technical Stack
Python 3.13, FastAPI, DuckDB, Pydantic v2, Docker (multi-stage), structured logging with structlog. Runs in-process with the property management ERP via webhook ingestion.

## Demo Flow (48h MVP)
1. Show raw email arriving (heating complaint from tenant EH-014)
2. Show Patcher making 4 surgical edits across 3 files (git diff — only the relevant lines change)
3. Show `_hermes_feedback.jsonl` receiving the ingest event
4. Show Linter extracting skill `heating-emergency-after-hours` into `06_skills.md`
5. Show outer loop proposal in `_pending_review.md` after simulated repeated failures
6. Show PM approval → schema mutation applied → schema_version bumped
