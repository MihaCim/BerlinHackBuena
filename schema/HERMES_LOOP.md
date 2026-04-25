---
name: hermes-self-improvement-loop
description: Two-loop self-improvement architecture for the BaC wiki. Inner loop extracts procedural skills from successful task trajectories. Outer loop mutates the wiki schema itself when retrieval failures recur. Both loops are async (post-commit), gated by PM approval where structural change occurs, and grounded in the per-Liegenschaft `_hermes_feedback.jsonl` event substrate. Read when implementing Linter, designing trigger logic, or evaluating whether the wiki is learning fast enough.
---

# Hermes Self-Improvement Loop

Two loops. Inner = procedural memory grows. Outer = schema itself evolves. Both async (post-commit). Both PM-gated where structural change occurs. Both grounded in `_hermes_feedback.jsonl`.

> **Hard rule:** No LLM at Patcher apply time. Both loops run as Linter jobs after the ingest commit lands.

---

## 1. Loop overview

| Loop | Cadence | Output | Substrate |
|---|---|---|---|
| **Inner — Skill Extraction** | per ingest where `complexity_score > 5` | `@skill` block in `06_skills.md` + bullet in `## Procedural Memory` of LIE/index.md (and HAUS if building-scoped) | task trajectory replay from `<LIE>/log.md` + last 50 JSONL entries |
| **Outer — Schema Mutation** | rolling-window failure score `≥ 3` per `(file, section)` OR fallback every 100 ingests | proposal in `<LIE>/_pending_review.md` → PM approves → schema + entity files mutate | `<LIE>/_hermes_feedback.jsonl` |

Inner loop is mature pattern (Karpathy `llm-wiki`, Anthropic skills.md). Outer loop is the novel piece: schema is data, mutates under empirical pressure. Karpathy's `llm-wiki` has only the inner loop. Buena's moat = the outer.

---

## 2. Feedback substrate — `_hermes_feedback.jsonl`

Path: `wiki/<LIE-id>/_hermes_feedback.jsonl`. Append-only. One JSON object per line. Newline-delimited. SQLite-importable via DuckDB `read_json_auto`.

### Event kinds (discriminator: `kind`)

```json
{"kind":"ingest","ts":"2026-04-25T14:32:11Z","ingest_id":"EMAIL-12044","event_type":"email.received","tool_calls":5,"complexity_score":5,"sections_read":[{"file":"wiki/LIE-001/02_buildings/HAUS-12/index.md","section":"Open Issues"}],"sections_patched":[{"file":"wiki/LIE-001/02_buildings/HAUS-12/index.md","section":"Open Issues","op":"upsert_bullet","key":"EH-014"}],"retrieval_success":true,"missing_context":null,"correction_applied":false,"patcher_commit":"a3f2c19"}

{"kind":"skill_extracted","ts":"2026-04-25T14:35:02Z","ingest_id":"EMAIL-12044","skill_id":"heating-emergency-after-hours","confidence":0.92,"linter_commit":"b4f5d20"}

{"kind":"correction","ts":"2026-04-25T15:10:44Z","ingest_id":"EMAIL-12044","corrected_by":"pm","diff_summary":"changed DL-003 → DL-007 in Procedural Memory","linter_commit":"c1a8f33"}

{"kind":"schema_proposal","ts":"2026-04-26T09:00:00Z","proposal_id":"PROP-0007","trigger_section":{"file":"wiki/LIE-001/02_buildings/HAUS-12/index.md","section":"Recent Events"},"trigger_reason":"recurring missing_context: contractor_phone_for_DL-007 (5x in 30 ingests)","affected_files":["02_buildings/HAUS-12/index.md","02_buildings/HAUS-13/index.md","02_buildings/HAUS-14/index.md"],"review_status":"pending"}

{"kind":"schema_approved","ts":"2026-04-26T11:30:00Z","proposal_id":"PROP-0007","approver":"mgorabbani","patcher_commits":["d3f1c87","e4a8b12"]}

{"kind":"schema_rejected","ts":"2026-04-26T11:30:00Z","proposal_id":"PROP-0008","approver":"mgorabbani","reason":"already covered by skill heating-emergency-after-hours; no schema change needed"}
```

### Append rules

- `ingest` event: written by Patcher, atomic with the PatchPlan commit. Idempotent on `ingest_id` (replay-safe).
- `skill_extracted`, `correction`, `schema_proposal`, `schema_approved`, `schema_rejected`: written by Linter on its own commits.
- File never edited, only appended. Each line is immutable. PII rules applied at write time (no full email bodies, no IBANs, only IDs + section refs).
- File-size cap: 50 MB. At cap → roll to `_hermes_feedback.<YYYY-Q>.jsonl` and reset.

### `retrieval_success` semantics

True when the located sections + extracted PatchPlan resolved the ingest without `correction` follow-up within 7 days. False when:

- Patcher refused all ops (no matching section).
- PatchPlan emitted but PM applied a `correction` event within 7 days.
- LLM returned `missing_context` in extraction step.

Default `null` for ingests where signal=LOW (logged but not patched).

---

## 3. Inner loop — Skill Extraction

### Trigger

Computed by Supervisor at ingest end:

```
complexity_score = num_tool_calls + 2 × num_source_docs + num_prose_merges
```

If `complexity_score > 5` OR `PatchPlan touched > 3 prose anchors` → enqueue Linter inner-loop job.

### Linter inner-loop job

1. Read trajectory from `<LIE>/log.md` for `ingest_id`.
2. Read last 50 JSONL entries for the LIE (related context, prior skills).
3. LLM distill: `name`, `description` (skills.md form), `When` trigger, ordered `Steps`, `Fallback`, `Source trajectories`, initial `confidence`.
4. Write `@skill` entry to `wiki/<LIE>/06_skills.md` using ONLY `name` + `description` frontmatter:

   ```yaml
   ---
   name: heating-emergency-after-hours
   description: Procedure for heating outages after 18:00 or weekends in any HAUS of LIE-001. Triggers on tenant emails containing "Heizung", "Warmwasser", "kalt" combined with timestamp ≥18:00 or weekend. Calls DL-007 (Notdienst), NOT DL-003 (Hausmeister has no key to heating room). Confidence 0.92 from 2 successful resolutions.
   ---
   **When:** Heizungsausfall ≥18:00 oder Wochenende.
   **Steps:**
   1. DL-007 Notdienst rufen (+49 30 555-0123).
   2. Mieter informieren, Bestätigung in MIE-XX/Contact History prepend_row.
   3. Aufwand in INV-* erwarten, INV reconcile.
   **Fallback (kein Ergebnis nach 60 min):** DL-Backup notrufen, EIG-* informieren.
   **Source trajectories:** EMAIL-11944, EMAIL-08812.
   **Confidence:** 0.92.
   ```

5. Surgical patch into `## Procedural Memory` of LIE/index.md (and affected HAUS/index.md if building-scoped):

   ```
   - **heating-emergency-after-hours:** DL-007 first, NOT DL-003 → @06_skills.md
   ```

6. Append `skill_extracted` event to JSONL.
7. Atomic commit: `linter(skill): heating-emergency-after-hours`.

### Skill confidence update

Each subsequent ingest where the skill applies and resolves without a `correction` event within 7 days bumps `confidence`:

```
confidence_new = (successful_uses + 1) / (total_uses + 1)
```

A `correction` event within the 7-day window decrements:

```
confidence_new = successful_uses / (total_uses + 1)
```

Skills with `confidence < 0.40` after `≥5` uses get flagged for PM review (NOT auto-deleted). Listed in `_pending_review.md` under `## Low-Confidence Skills`.

---

## 4. Outer loop — Schema Mutation

### Trigger (hybrid: score-primary, counter-fallback)

Linter runs nightly. Per LIE:

```
section_failure_score(file, section) =
    1 × count(retrieval_success=false where section ∈ sections_read in last 30 ingests)
  + 2 × count(correction where section ∈ sections_patched in last 30 ingests)
  + 1 × count(missing_context recurrence keyed to section in last 30 ingests)
```

Trigger structural eval if:
- ANY `(file, section)` pair has `failure_score ≥ 3`, OR
- No structural eval has fired in the last 100 ingests (fallback against quiet-period drift).

### Linter outer-loop job

1. DuckDB import last 30 JSONL `ingest` entries for the LIE.
2. Group failures by `(file, section)` and `missing_context` patterns.
3. LLM eval: propose minimal schema mutation. One of:
   - **Add new section** to file type (e.g. "Contractor Quick Reference").
   - **Add new keyed-bullet/row convention** within an existing section.
   - **Split oversized section** by sub-key (e.g. by floor).
   - **Adjust per-section freshness/token budget**.
   - **Rename section header** (rare; breaks all existing files — must justify).
   - **No-op** (failure cluster better solved by a skill, not schema change).

4. Write proposal to `wiki/<LIE>/_pending_review.md`:

   ```markdown
   ## Schema Mutation Proposal — PROP-0007 — 2026-04-26 (Linter)

   **Trigger:** section "Recent Events" in HAUS-12/index.md showed `retrieval_success=false` in 4 of last 30 ingests; `missing_context` recurrence: "contractor_phone_for_DL-007" (5×).

   **Proposed change:** Add new keyed-bullet convention `- 📞 **{DL-id}:** {phone} [^source]` inside existing "Contractors Active" section in HAUS index.md schema. No new section. Phone resolves inline.

   **Affected files:**
   - `schema/WIKI_SCHEMA.md` (add convention to §5)
   - `schema/CLAUDE.md` (add to keyed-bullet table)
   - `wiki/LIE-001/02_buildings/HAUS-12/index.md`
   - `wiki/LIE-001/02_buildings/HAUS-13/index.md`
   - `wiki/LIE-001/02_buildings/HAUS-14/index.md`

   **Archive-First:** Tier A (additive change, no removal).

   **Estimated cost:** 5 file patches, 0 archive entries.

   **Alternatives considered:**
   - Skill `lookup-contractor-phone`: rejected (info is structural, not procedural).
   - New file `contractors_quickref.md`: rejected (extra hop, breaks single-index discovery).

   **PM action:** approve / reject / modify.
   ```

5. Append `schema_proposal` event to JSONL.

### PM approval workflow

PM appends to the proposal block:

```markdown
**Approved by:** mgorabbani — 2026-04-26 11:30
```

(or `**Rejected by:** ... — reason: ...`; or modifies the proposal body in-place with edits, then approves the modified version).

Linter polls `_pending_review.md` for newly-approved proposals → applies the schema change:

1. Schema text changes → patch `schema/WIKI_SCHEMA.md` + `schema/CLAUDE.md` via Patcher ops (the schema docs themselves are wiki-managed).
2. Entity-file template changes → patch all affected `.md` files via the standard ops set.
3. Section removal → invoke Archive-First **Tier B** (5-step with git tag — see `WIKI_SCHEMA.md §16`).
4. Append `schema_approved` event to JSONL.
5. Atomic commit: `linter(schema): apply PROP-0007 — contractor phone bullets`.
6. Bump `schema_version` in `_state.json` and append a row to `## Template-Versionshistorie` in `schema/WIKI_SCHEMA.md` (Karpathy format: `## [YYYY-MM-DD HH:MM:SS] schema_version=N.N.N`).

---

## 5. Hard constraints (Linter refuses even if LLM proposes)

- **Cross-tenant changes.** Mutating LIE-002 from a LIE-001 trigger.
- **`# Human Notes` boundary.** No write past it. Period.
- **Section removal without Tier B Archive-First.** Git tag is mandatory.
- **Frontmatter contract change.** `name` + `description` only. Always.
- **Directory layout numbering.** `01_management/` … `07_timeline.md` is invariant.
- **Sidecar location.** `_state.json` lives at LIE root, never moves.
- **Footnote rules.** Provenance-only-in-`## Provenance`. Two-hop trace mandatory.
- **Auto-apply without `**Approved by:**`.** Proposal sits indefinitely until PM acts.
- **Vocabulary removal.** `schema/VOCABULARY.md` is append-only.

---

## 6. Querying the loop (DuckDB)

```sql
-- one-time import (re-run on new entries; cheap)
CREATE OR REPLACE TABLE hermes_feedback AS
SELECT * FROM read_json_auto(
  'wiki/LIE-001/_hermes_feedback.jsonl',
  format='newline_delimited'
);

-- top failing sections in last 30 ingests
SELECT
  read.file,
  read.section,
  COUNT(*) AS failures
FROM hermes_feedback,
     UNNEST(sections_read) AS u(read)
WHERE kind = 'ingest'
  AND retrieval_success = false
  AND ts > now() - INTERVAL 30 DAY
GROUP BY read.file, read.section
ORDER BY failures DESC
LIMIT 10;

-- skill confidence trend
SELECT
  skill_id,
  COUNT(*)        AS extractions,
  AVG(confidence) AS avg_conf,
  MAX(ts)         AS last_extraction
FROM hermes_feedback
WHERE kind = 'skill_extracted'
GROUP BY skill_id
ORDER BY avg_conf DESC;

-- recurring missing-context patterns
SELECT
  missing_context,
  COUNT(*) AS occurrences
FROM hermes_feedback
WHERE kind = 'ingest' AND missing_context IS NOT NULL
GROUP BY missing_context
HAVING occurrences >= 3
ORDER BY occurrences DESC;
```

---

## 7. MVP cut (48h hackathon)

| Capability | Status | Demo proof |
|---|---|---|
| JSONL append on ingest | **must** | `tail -1 _hermes_feedback.jsonl` after staged ingest |
| Inner loop skill extraction | **must** | new `@skill` block + bullet in `## Procedural Memory` |
| Bullet patch into Procedural Memory | **must** | `git diff LIE-001/index.md` shows 1 added line |
| `_pending_review.md` proposal example | **must** | static example committed to repo for visual |
| Outer loop nightly Linter pass | **stretch** | manual `linter run-eval --lie LIE-001` on stage |
| PM approval + auto-apply | **post-MVP** | mention in voiceover only |
| Schema mutation propagation | **post-MVP** | mention in voiceover only |

The outer-loop story is the architectural moat even when not fully automated in 48h. Manual `linter run-eval` is enough to demo the JSONL → proposal flow live in front of judges.

---

## 8. Why two loops, not one

Single loop (skill extraction only) treats the schema as a constant. Adequate for static domains.

Real property management is not static: regulations change (heat-pump retrofit rules post-GEG-2024), building events introduce new categories (E-mobility charger compliance), Verwalter conventions drift over years. A frozen schema accumulates retrieval misses indefinitely — agent quality decays even as the wiki content grows.

Outer loop closes that gap. Every retrieval miss is a vote for schema mutation. PM is the human gate (one-click approval). LLM is the proposal generator. Schema becomes a versioned, evolved artifact — full Archive-First Tier B reconstruction available for any prior state.

This is the architectural distinction from `llm-wiki`: not the wiki content, the *wiki evolution mechanism*.

---

## 9. Failure-mode notes

- **Loop oscillation.** If outer-loop adds a section that inner-loop later finds redundant, the outer loop will eventually propose its removal. Tier B Archive-First makes the round-trip safe but expensive. Mitigation: outer-loop LLM prompt explicitly asks "would a skill solve this?" first.
- **JSONL replay drift.** If the ingest pipeline is re-run from raw, JSONL must be cleared (idempotency on `ingest_id` would otherwise double-count). `linter reset --lie LIE-001 --since YYYY-MM-DD` handles this.
- **PM never approves.** Proposals pile up in `_pending_review.md`. Linter rate-limits to max 3 open structural proposals per LIE; further triggers wait until existing ones are decided.
- **Skill drift.** A skill with `confidence > 0.9` initially can decay if circumstances change (DL-007 closes, replaced by DL-019). Linter watches `correction` events keyed to skill_ids; drops confidence proportionally; flags below 0.40 for PM.
