# Wiki Schema — BerlinHackBuena

Living-context wiki for German WEG property management. Pure Karpathy `llm-wiki` pattern + Anthropic Agent Skills (skills.md) frontmatter discipline + Buena's "single Context Markdown File per property" mandate.

**One property = one folder rooted at `wiki/<LIE-id>/`. Entry file = `<LIE-id>/index.md`.** Sub-mds inside the folder hold specialized depth. Markdown is canonical at every storage tier; DuckDB sidecars are derived caches.

---

## 1. Property = Liegenschaft

In German WEG law, the Liegenschaft (legal entity / WEG) is the unit of management:
- ONE Verwalter contract per Liegenschaft
- ONE ETV (Eigentümerversammlung), ONE Wirtschaftsplan, ONE BKA
- ONE WEG-Konto + Rücklage at Liegenschaft level
- Eigentümer can own units across MULTIPLE Gebäude in the same Liegenschaft
- Dienstleister contracted by the WEG, serve all Gebäude

Therefore Buena's "property" = Liegenschaft. Buildings are subordinate. Layout reflects this.

---

## 2. Directory layout

```
wiki/
├── index.md                          # global catalog (multi-WEG ready)
├── log.md                            # global event log
├── schema/
│   ├── CLAUDE.md                     # ingestion system prompt
│   ├── style.md                      # learned PM preferences
│   └── skills.md                     # extracted skills (skills.md form)
│
└── LIE-001/                          # ★ one property = one folder
    ├── index.md                      # ★ THE Context.md (Buena deliverable)
    ├── _state.json                   # sidecar state (last_patched, counts)
    ├── log.md                        # property-scoped event log
    ├── _pending_review.md            # contradictions awaiting PM
    │
    ├── 01_management/                # WEG-scoped governance
    │   ├── verwaltervertrag.md
    │   ├── etv_protokolle.md
    │   ├── beirat.md
    │   ├── wirtschaftsplan.md
    │   └── bka.md
    │
    ├── 02_buildings/
    │   ├── HAUS-12/
    │   │   ├── index.md              # building summary
    │   │   ├── physical.md
    │   │   ├── issues.md
    │   │   └── units/
    │   │       └── EH-014.md         # unit dossier
    │   ├── HAUS-13/…
    │   └── HAUS-14/…
    │
    ├── 03_people/
    │   ├── eigentuemer/
    │   │   └── EIG-014.md            # owner can span buildings
    │   └── mieter/
    │       └── MIE-014.md
    │
    ├── 04_dienstleister/
    │   └── DL-007.md
    │
    ├── 05_finances/
    │   ├── overview.md
    │   ├── reconciliation.md
    │   └── invoices/
    │       └── 2026-04/
    │           └── INV-02103.md
    │
    ├── 06_skills.md                  # procedural memory (Hermes loop output)
    ├── 07_timeline.md                # full chronology
    │
    └── _archive/                     # pruned long-tail
        └── timeline-2024.md
```

Numbered prefixes (`01_..07_`) force natural reading order in file explorers and align with importance ranking.

Multi-tenant production tier prepends customer prefix: `wiki/<verwalter>/LIE-001/...`. Same recursive pattern.

---

## 3. Frontmatter contract — skills.md form

Every wiki .md uses **only** `name` + `description` per Anthropic Agent Skills spec (April 2026):

- `name`: ≤64 chars, lowercase letters/numbers/hyphens. Matches the file's purpose.
- `description`: ≤1024 chars, third-person voice. Pushy + specific. Names entities + use cases. Tells the agent **when to read this file**.

State + identity + hierarchy live in the **`_state.json` sidecar** and inside body content, not in frontmatter. Frontmatter stays tiny + stable.

### Example — `LIE-001/index.md`

```yaml
---
name: lie-001-immanuelkirchstr-26
description: Living context for WEG Immanuelkirchstraße 26, 10405 Berlin (Liegenschaft LIE-001). 3 buildings (HAUS-12 Vorderhaus, HAUS-13 Seitenflügel, HAUS-14 Hinterhaus), 52 units, 35 owners, 26 tenants, 16 service providers. Verwalter Huber & Partner. First stop for ANY question about this property — buildings, units, owners, tenants, service providers, finances, ETV, BKA, Hausgeld, Rücklage, contractor relationships. Routes to detail via @imports.
---
```

### Example — building entry

```yaml
---
name: haus-12-vorderhaus
description: Vorderhaus of WEG Immanuelkirchstraße 26 (parent LIE-001). 19 apartments EH-001..EH-019, Baujahr 1908, no elevator. Heizung Buderus GB 162 (2019). Hausmeister DL-003. Use for building-specific questions: physical state, roof, heating, building-wide repairs, fire safety, building-level tenant issues. For owner/finance/ETV questions, route up to LIE-001/index.md.
---
```

### Example — unit dossier

```yaml
---
name: eh-014-haus-12-2og-links
description: Apartment EH-014 in HAUS-12 (Vorderhaus), 2. OG links, 67.4 m², 2.5 Zimmer, MEA 18.7. Current tenant MIE-014 Anna Müller (since 2023-08-01, Kaltmiete €894). Current owner EIG-009 Klaus Schmidt. Use for unit-specific history: tenant timeline, repair tickets, payment history. Active issue: 🔴 heating outage since 2026-04-23. Cross-references DL-007 (heating contractor) and EIG-009 (owner).
---
```

### Example — person dossier

```yaml
---
name: eig-014-maria-weber
description: Eigentümerin Maria Weber, owns EH-014 (HAUS-12) and EH-027 (HAUS-13) — two units across two buildings. Beirat member, holds SEV-Mandat. Email m.weber@example.de. Pays Hausgeld punctually. Conservative voter in ETV. Use for owner-specific queries; cross-references both HAUS-12 and HAUS-13 because of multi-building ownership.
---
```

### Example — skill (in `06_skills.md` or `schema/skills.md`)

```yaml
---
name: heating-emergency-after-hours
description: Procedure for heating outages after 18:00 or weekends in any HAUS of LIE-001. Triggers on tenant emails containing "Heizung", "Warmwasser", "kalt", "kein Wasser" combined with timestamp ≥18:00 or weekend. Calls DL-007 (Notdienst), NOT DL-003 (Hausmeister has no key to heating room). Confidence 0.92 from 2 successful resolutions. Extracted via Hermes loop on 2026-04-22 from EMAIL-11944 (7-step trajectory).
---
```

---

## 4. Body convention — plain markdown, heading-delimited

No XML anchor markers. No bespoke syntax. Pure Karpathy: standard markdown headings define sections. Patcher targets sections by heading text.

### Body skeleton — `LIE-001/index.md`

```markdown
---
name: lie-001-immanuelkirchstr-26
description: <as above>
---

# WEG Immanuelkirchstraße 26 — Living Context

> 1 Verwalter, 3 Häuser, 52 Einheiten, 35 Eigentümer, 26 Mieter, 16 Dienstleister. WEG-Konto Postbank, Rücklage BayernLB.

**See also:** @01_management/etv_protokolle.md · @05_finances/overview.md · @06_skills.md

## Buildings

| ID | Name | EH | Health | Open |
|---|---|---|---|---|
| HAUS-12 | Vorderhaus | 19 | 0.78 | 🔴 1 |
| HAUS-13 | Seitenflügel | 17 | 0.92 | — |
| HAUS-14 | Hinterhaus | 16 | 0.85 | 🟡 1 |

## Bank Accounts

- WEG-Konto: DE02 1001 0010 0123 4567 89 (Postbank)
- Rücklage: DE12 1203 0000 0098 7654 32 (BayernLB)
- Verwalter: DE89 3704 0044 0532 0130 00 (Commerzbank)

## Open Issues

- 🔴 **EH-014:** Heizung defekt seit 2026-04-23 (HAUS-12, MIE-014) [^EMAIL-12044]
- 🟡 **MIE-019:** Mieterhöhung Widerspruch — Frist 2026-05-15 (HAUS-13) [^LTR-0128]
- 🟢 **BKA-2024:** 2 Rückfragen offen [^LTR-0089]

## Recent Events

| Datum | HAUS | Typ | Summary | Quelle |
|---|---|---|---|---|
| 2026-04-25 14:32 | HAUS-12 | email | Heizungsbeschwerde EH-014 | [^EMAIL-12044] |
| 2026-04-23 11:08 | HAUS-12 | invoice | Boiler-Service DL-007 €380 | [^INV-02103] |

## Procedural Memory

- **heating-emergency-after-hours:** DL-007 zuerst, nicht DL-003 → @06_skills.md
- **water-damage-emergency:** Foto + IBAN sofort an DL-011 → @06_skills.md

## Provenance

[^EMAIL-12044]: normalize/eml/2026-04/EMAIL-12044.md
[^INV-02103]: normalize/pdf/2026-04/INV-02103.md
[^LTR-0128]: normalize/pdf/2026-04/LTR-0128.md
[^LTR-0089]: normalize/pdf/2025-03/LTR-0089.md

# Human Notes

<!-- Everything below this h1 is sacred, agent never writes here. -->
```

---

## 5. Surgical-update conventions (the key insight)

Patches happen at **bullet/row level**, not section level. Section-replace destroys human edits. Per Buena: "surgically updated without destroying human edits."

### Keyed bullets (agent-managed)

Format: `- {emoji} **{ID}:** {content} [^source]`

```markdown
- 🔴 **EH-014:** Heizung defekt seit 2026-04-23 [^EMAIL-12044]
- 🟡 **MIE-019:** Mieterhöhung Widerspruch [^LTR-0128]
- (PM) Tenant called 3x today, escalated.       ← human, preserved verbatim
```

Patcher rule: bullet matching `- {emoji} **{ID}:** ...` = agent-managed. Upsert by ID. Anything else = human, preserved.

### Keyed table rows

```markdown
| ID | Tenant | Status |
|---|---|---|
| EH-014 | MIE-014 | 🔴 Heizung |
| EH-015 | MIE-015 | ✓ |
```

Patcher rule: first cell = key. Upsert row by matching first cell. Other rows untouched.

### Ring buffers (e.g. Recent Events)

Append-only at top of table. Prune oldest beyond max=50. Older rows → `07_timeline.md`. Older than that → `_archive/`.

### Footnotes

```markdown
[^EMAIL-12044]: normalize/eml/2026-04/EMAIL-12044.md
```

Patcher rule: upsert by `[^KEY]:` prefix. Idempotent. GC drops entries with `ref_count == 0`.

### Boundary marker — `# Human Notes`

Sacred. Patcher refuses any write past this h1. Stripped from any LLM read.

---

## 6. Patcher op set

All ops = pure regex/line operations. Zero LLM at apply time. Idempotent. Deterministic.

| Op | Granularity | Touches | Preserves |
|----|-------------|---------|-----------|
| `upsert_bullet(file, section, key, line)` | one bullet | only that bullet line | all other bullets (incl. human) |
| `delete_bullet(file, section, key)` | one bullet | only that bullet line | rest |
| `upsert_row(file, section, key, row)` | one table row | only that row | rest of table |
| `delete_row(file, section, key)` | one row | only that row | rest |
| `prepend_row(file, section, row)` | one row at top | inserts after `\|---\|` separator | rest |
| `prune_ring(file, section, max)` | tail rows | removes oldest beyond max | head + middle |
| `upsert_footnote(file, key, value)` | one footnote line | only that line | rest |
| `gc_footnotes(file)` | unreferenced footnotes | drops `ref_count == 0` | rest |
| `update_state(field, value)` | sidecar `_state.json` field | only that field | rest of state |

A `PatchPlan` = list of ops. Applied atomically (tempfile → fsync → rename → single git commit).

---

## 7. State sidecar — `_state.json`

Per-property metadata, derived, machine-managed.

```json
{
  "id": "LIE-001",
  "type": "liegenschaft",
  "schema_version": 1,
  "last_patched": "2026-04-25T14:32:11Z",
  "patcher_commit": "a3f2c19",
  "health_score": 0.78,
  "open_issues_count": 3,
  "overdue_invoices_count": 1,
  "pending_review_count": 0,
  "buildings": ["HAUS-12", "HAUS-13", "HAUS-14"],
  "files": {
    "index.md":                      {"sha256": "...", "last_patched": "..."},
    "02_buildings/HAUS-12/index.md": {"sha256": "...", "last_patched": "..."}
  }
}
```

Dataview reads this for the global Building Health Score dashboard. If lost, regenerate from wiki content.

---

## 8. Health score (derived)

Computed by Linter on every patch. Pure code, no LLM.

```
health = 1.0
       - 0.10 × open_issues_count
       - 0.20 × overdue_invoices_count
       - 0.05 × stale_facts_count          (last_patched > 90d on critical section)
       - 0.10 × pending_review_count
clamped to [0, 1]
```

Written to `_state.json`. Dataview aggregates.

---

## 9. Compactness rules (non-negotiable)

The wiki must stay token-efficient.

- Bullets over prose. No multi-sentence paragraphs except in summaries.
- Tables for repeated rows. Owners, tenants, units, recent events = tables.
- `Recent Events` ring buffer max=50. Older → `07_timeline.md`.
- Per-tenant payment history capped at 12 months. Older → archive.
- No redundant cross-restating. Detail lives in the dedicated entity page; index references.
- Footnote provenance once per file, in `## Provenance` section only.
- Truncate quotes ≤200 chars. Full text remains in `normalize/eml/...`.
- Target sizes: `index.md` ≤30 KB. Entity pages ≤15 KB. Concept pages ≤30 KB. Hard cap 50 KB any file → archive overflow.

If a patch would push a file over target, run a compaction pass first: archive stale rows, regenerate ring buffers, drop unreferenced footnotes.

---

## 10. Conflict policy

If a new fact contradicts existing keyed bullet/row:

1. Do NOT overwrite.
2. Append a conflict entry to `_pending_review.md` with both claims, both sources, timestamps.
3. Log it in `log.md`.
4. Leave the bullet/row unchanged.
5. Continue with non-conflicting ops.

A human or the Linter resolves later (with bigger context).

---

## 11. Ingestion-side index — DuckDB `wiki_chunks`

To make ingestion fast + deterministic, the same DuckDB instance running bank/invoice queries also indexes the wiki. Powers both ingestion-side section locating and read-side search.

```sql
CREATE TABLE wiki_chunks (
  path          VARCHAR,           -- wiki/LIE-001/02_buildings/HAUS-12/index.md
  property_id   VARCHAR,           -- LIE-001
  section       VARCHAR,           -- "Open Issues"
  line_start    INT,
  line_end      INT,
  content       TEXT,              -- the section body
  entity_refs   VARCHAR[],         -- [MIE-014, EH-014, HAUS-12, DL-007]
  footnote_ids  VARCHAR[],         -- [EMAIL-12044, INV-02103]
  version       INT,
  last_patched  TIMESTAMP,
  sha256        VARCHAR
);

CREATE INDEX wiki_chunks_property ON wiki_chunks(property_id);
CREATE INDEX wiki_chunks_path     ON wiki_chunks(path);

INSTALL fts; LOAD fts;
PRAGMA create_fts_index('wiki_chunks', 'path||section', 'content', stemmer='german');
```

Built by parsing each section with regex `[A-Z]{2,4}-\d{3,5}` → entity refs. Re-indexed on every Patcher commit (per-file, ~10 ms).

### Ingestion lookup

```sql
-- Find target sections referencing entities from a new event
SELECT DISTINCT path, section, line_start
FROM wiki_chunks
WHERE property_id = 'LIE-001'
  AND (list_contains(entity_refs, 'MIE-014')
    OR list_contains(entity_refs, 'EH-014')
    OR list_contains(entity_refs, 'HAUS-12'));

-- Conflict scan
SELECT content FROM wiki_chunks
WHERE list_contains(entity_refs, 'EH-014')
  AND content ILIKE '%Heizung%';

-- Footnote dedupe
SELECT 1 FROM wiki_chunks WHERE list_contains(footnote_ids, 'EMAIL-12044');
```

Same table powers BM25 search for read-side queries via FTS5.

---

## 12. Wikilinks and imports

### Wikilinks (Obsidian-friendly)

```markdown
[[02_buildings/HAUS-12/index]]
[[03_people/mieter/MIE-014]]
[[../HAUS-13/units/EH-027]]
```

Obsidian resolves filename-only or relative paths. Graph view free.

### CLAUDE.md-style imports (inline references)

```markdown
**See also:** @01_management/etv_protokolle.md · @05_finances/overview.md · @06_skills.md
```

`@filename` references = explicit "this file depends on these." Agent fetches them on demand. Lives in body where contextually relevant, not in a separate frontmatter list.

---

## 13. Path resolution rules (deterministic)

Agents never guess paths. Pure function:

```
property_id = LIE-001
→ entry:    wiki/LIE-001/index.md
→ state:    wiki/LIE-001/_state.json

building_id = HAUS-12 (parent: LIE-001)
→ wiki/LIE-001/02_buildings/HAUS-12/index.md

unit_id = EH-014 (in HAUS-12)
→ wiki/LIE-001/02_buildings/HAUS-12/units/EH-014.md

owner_id = EIG-014 (cross-building)
→ wiki/LIE-001/03_people/eigentuemer/EIG-014.md

tenant_id = MIE-014
→ wiki/LIE-001/03_people/mieter/MIE-014.md

dienstleister_id = DL-007
→ wiki/LIE-001/04_dienstleister/DL-007.md
```

---

## 14. Why this works

- **Buena spec:** "single Context Markdown File per property" → `LIE-001/index.md`. Folder = its imports.
- **Surgical patches:** keyed bullets + table rows = bullet-level edits, ~7 lines changed per ingest, never destroys human edits.
- **Karpathy purity:** entity pages + concept pages + log + index + schema dir, with skills.md frontmatter on every file.
- **Skills.md purity:** only `name` + `description` in frontmatter, ≤1024 chars description, third-person voice, progressive disclosure.
- **WEG law fit:** Liegenschaft is the property; cross-building owners modeled correctly; bank/finances/ETV at LIE root.
- **Multi-tenant ready:** prepend `wiki/<verwalter>/<lie>/...`. Same recursive pattern.
- **Token-cheap:** description = discovery layer, body = read on demand, anchor lookup via DuckDB index.
- **Self-contained:** zip the LIE folder = portable backup.

---

## 15. Per-section metadata annotation

Each major section in any wiki `.md` MAY carry an HTML-comment metadata line immediately above its `## Heading`. Optional but Linter-respected when present. HTML comments are valid markdown, hidden from any renderer.

Format:

```markdown
<!-- meta: tier=1 freshness=14d token_ceiling=500 -->
## Open Issues
```

Keys:

| Key             | Type        | Default                    | Purpose                                                                  |
|-----------------|-------------|----------------------------|--------------------------------------------------------------------------|
| `tier`          | `0` / `1` / `2` | from §15.1 table        | retrieval priority for chunk-level fan-out                                |
| `freshness`     | `<N>d|w|m|y` | from §15.1 table          | Linter flags `stale_facts_count++` if `last_patched > freshness`          |
| `token_ceiling` | int          | from §15.1 table          | Linter alerts at >120% of ceiling, schedules split on recurring breach    |

Linter regex: `<!--\s*meta:\s*(?:tier=(\d+)\s*)?(?:freshness=(\d+[dwmy])\s*)?(?:token_ceiling=(\d+)\s*)?-->`

### 15.1 Defaults table

| File type        | Section              | Tier | Freshness | Token ceiling |
|------------------|----------------------|------|-----------|---------------|
| LIE/index.md     | Buildings            | 0    | 30d       | 200           |
| LIE/index.md     | Bank Accounts        | 2    | 365d      | 200           |
| LIE/index.md     | Open Issues          | 0    | 7d        | 500           |
| LIE/index.md     | Recent Events        | 1    | 1d        | 500           |
| LIE/index.md     | Procedural Memory    | 1    | 180d      | 500           |
| LIE/index.md     | Provenance           | 2    | n/a       | 500           |
| HAUS/index.md    | Summary              | 2    | 365d      | 300           |
| HAUS/index.md    | Units                | 2    | 90d       | 500           |
| HAUS/index.md    | Open Issues          | 0    | 7d        | 500           |
| HAUS/index.md    | Recent Events        | 1    | 1d        | 500           |
| HAUS/index.md    | Contractors Active   | 1    | 90d       | 400           |
| HAUS/index.md    | Provenance           | 2    | n/a       | 500           |
| EH-XX.md         | Unit Facts           | 2    | 365d      | 200           |
| EH-XX.md         | Current Tenant       | 1    | 30d       | 150           |
| EH-XX.md         | Current Owner        | 1    | 365d      | 150           |
| EH-XX.md         | History              | 1    | 1d        | 500           |
| EIG-XX.md        | Contact              | 2    | 365d      | 150           |
| EIG-XX.md        | Units Owned          | 2    | 90d       | 300           |
| EIG-XX.md        | Payment History      | 1    | 30d       | 500           |
| MIE-XX.md        | Tenancy              | 2    | 365d      | 200           |
| MIE-XX.md        | Payment History      | 1    | 30d       | 500           |
| DL-XX.md         | Services             | 2    | 365d      | 200           |
| DL-XX.md         | Recent Invoices      | 1    | 90d       | 400           |
| DL-XX.md         | Performance Notes    | 1    | 180d      | 300           |

Override only when a specific section deviates from the file-type default. Defaults apply silently otherwise.

### 15.2 Linter enforcement

```sql
-- stale_facts detection (uses metadata + last_patched from wiki_chunks)
SELECT path, section
FROM wiki_chunks
WHERE last_patched < now() - INTERVAL '<freshness_value>';
```

Result counted into `stale_facts_count` of `_state.json`, factored into `health_score`.

```sql
-- token-ceiling breach detection
SELECT path, section, length(content) AS bytes
FROM wiki_chunks
WHERE bytes > token_ceiling * 4 * 1.2  -- ~4 bytes per token, +20% slack
ORDER BY bytes DESC;
```

Recurring breach (>3 consecutive nightly runs) → outer-loop trigger to propose section split.

---

## 16. Archive-First Protocol — two tiers

Replaces the simple `_archive/` move. Granularity-matched.

### Tier A — Bullet/row removal (common path)

Used when: issue resolved (status `gelöst` > 60 d), tenant moved, ring-buffer prune, footnote GC.

```
1. prepend_row → 07_timeline.md (only if not already present)
2. delete_bullet / delete_row via Patcher
3. log entry in <LIE>/log.md: "archive(tier-a): EH-014 issue closed"
4. gc_footnotes on next commit
```

No git tag. Reconstruction: `07_timeline.md` + git history. Cheap, frequent.

### Tier B — Section / schema removal (rare)

Used when: outer-loop schema mutation removes a section, structural deprecation, sensitive-data redaction.

```
STEP 1. Snapshot section to:
        _archive/<file_path_slug>/YYYY-MM-DD_<section>_v<N>.md
        File MUST include: section content + all referenced provenance footnotes.

STEP 2. Create git tag:
        archive/<LIE-id>/<file_path_slug>/<section>/v<N>

STEP 3. Append a row to the `archive_index` section in the file's index.md
        (or LIE/index.md if the file itself is removed).

STEP 4. Append entry to <LIE>/log.md with reason + patcher_commit.

STEP 5. Apply removal via Patcher.
```

Reconstruction: `git checkout <archive-tag> -- <path>` returns the exact pre-removal state.

### Trigger gate

- **Tier A:** automatic via prune rules and resolved-status thresholds.
- **Tier B:** ONLY via approved `_pending_review.md` proposal (outer-loop schema mutation or explicit PM request).

---

## 17. Hermes self-improvement loop (pointer)

Two loops:

- **Inner loop** = procedural skill extraction per high-complexity ingest (`complexity_score > 5`). Async Linter job. Output: `@skill` block in `06_skills.md` + bullet in `## Procedural Memory`.
- **Outer loop** = schema mutation when retrieval failures recur. Trigger: any `(file, section)` `failure_score ≥ 3` over rolling 30 ingests, fallback every 100 ingests. Output: proposal in `_pending_review.md`, PM-gated.

Substrate: `wiki/<LIE>/_hermes_feedback.jsonl` (append-only, SQLite-importable).

Per-event JSONL append is part of the canonical Patcher commit (see `schema/CLAUDE.md` step 7).

**Full spec:** [`schema/HERMES_LOOP.md`](HERMES_LOOP.md).

---

## 18. Decisions & rejected alternatives

Append-only record of architectural choices, with rejected alternatives. Provenance for the canonical schema.

### 18.1 Liegenschaft root vs Building root

**Decision:** Liegenschaft root. `wiki/<LIE-id>/index.md` is THE Buena deliverable. Buildings are subfolders (`02_buildings/HAUS-XX/`).

**Rejected:** Building root (`wiki/<LIE>/<HAUS>/index.md` as deliverable, WEG-scoped facts duplicated per HAUS).

**Why:** WEG law: ONE Verwalter / ETV / Wirtschaftsplan / BKA / Konto per Liegenschaft. Eigentümer can own units across multiple Gebäude in the same LIE. Building root would triplicate ETV/Hausgeld/Rücklage and break cross-building owner queries. Liegenschaft = canonical unit of management.

**Source of rejected idea:** `template_index.md` (root file path `wiki/<LIE>/<HAUS>/index.md`).

### 18.2 Bullet/row keyed patches vs section-anchor patches

**Decision:** bullet/row keyed surgical patches. Section heading = location target. Patch granularity = `- 🔴 **EH-014:** ...` line or table row.

**Rejected:** XML anchor markers `<!-- @section:KEY version=N -->` ... `<!-- @end:KEY -->` with section-level rewrites and version bumps.

**Why:** Buena hard problem #2 = "surgical updates without destroying human edits." Section-level anchors expose the entire section to LLM rewrite — any human inline annotation inside is at risk on every patch. Bullet/row keys touch only the line matching the key. Human-authored lines (no `**ID:**` prefix) preserved verbatim. Pure regex/line ops, zero LLM at apply time.

**Source of rejected idea:** `template_index.md` `<!-- @section -->` convention.

### 18.3 skills.md frontmatter vs heavy state frontmatter

**Decision:** `name` + `description` ONLY in frontmatter (Anthropic Agent Skills spec). State → `_state.json` sidecar.

**Rejected:** inline state YAML (`id`, `parent`, `children`, `health_score`, `open_issues_count`, `hermes_nudge_counter`, `retrieval_profile`, etc.).

**Why:** frontmatter must stay stable for embedding/index caches. State mutates on every ingest; inline state would dirty markdown git history with state-only commits and break cache reuse. skills.md form gives a one-call discovery primitive — agent reads frontmatter, decides if file is relevant, drills body on demand. Token-cheap.

**Source of rejected idea:** `template_index.md` extensive YAML block.

### 18.4 Hybrid score+fallback trigger vs mod-N counter

**Decision:** outer-loop fires when any `(file, section)` failure_score ≥ 3 in rolling 30-event window. Fallback: force eval if no eval has fired in last 100 ingests.

**Rejected:** `nudge_counter mod 15 == 0` periodic trigger.

**Why:** mod-N is arbitrary — 15 routine ingests waste a structural eval; 15 ingests against one stuck section delays a needed fix. Score-based fires when warranted. Fallback prevents indefinite quiet-period drift.

**Source of rejected idea:** `template_index.md` mod-15 nudge.

### 18.5 Async Linter for skill extraction vs inline Patcher extraction

**Decision:** skill extraction runs in async Linter job AFTER the Patcher commit. Patcher only appends one JSONL line atomically.

**Rejected:** inline LLM skill extraction inside the Patcher commit.

**Why:** ingest path must be deterministic and fast. LLM in critical path = unbounded latency + retry loops = stuck commits. Async Linter consumes JSONL, runs LLM, commits skill patch on its own.

**Source of rejected idea:** `template_index.md` Step 5 of Patcher per-ingest checklist (inline `skill extraction`).

### 18.6 Two-tier Archive-First vs single-tier with universal git tag

**Decision:** Tier A (bullet/row, no tag, log entry only) + Tier B (section/schema, full 5-step with git tag).

**Rejected:** universal Archive-First with git tag for every removal.

**Why:** universal tagging would create thousands of tags per year on a busy LIE (every resolved issue, every prune). Git ref-space pollution with no reconstruction value beyond `log.md`. Tier-A removals are reconstructable from `07_timeline.md` + git history; Tier-B (rare, schema-impacting) earns the tag.

**Source of rejected idea:** `template_index.md` universal Archive-First.

### 18.7 `# Human Notes` h1 vs `## PM Notes` h2 boundary

**Decision:** `# Human Notes` h1 boundary, sacred, Patcher refuses any write past it, stripped from any LLM read.

**Rejected:** `## PM Notes` h2 boundary.

**Why:** h1 = file-level boundary, unambiguous. h2 risks confusion with siblings of `## Provenance` etc. Stronger signal to both LLM (system-prompt enforced) and Linter (regex-enforced).

**Source of rejected idea:** `template_index.md`.

### 18.8 Ideas borrowed from `template_index.md`

What we kept from the rejected proposal:

| Idea                                                           | Where ported                                                |
|----------------------------------------------------------------|-------------------------------------------------------------|
| Per-section freshness ceiling                                  | §15 (HTML-comment annotation + defaults table)              |
| Per-section token ceiling                                      | §15                                                         |
| Tier 0/1/2 retrieval priority                                  | §15.1                                                       |
| Empty-state lines                                              | `schema/VOCABULARY.md` (canonical empty-state table)         |
| Controlled-vocabulary single source                            | `schema/VOCABULARY.md`                                      |
| German legal mapping                                           | `schema/LEGAL_MAP.md`                                       |
| Two-loop self-improvement architecture                         | `schema/HERMES_LOOP.md` (refined: score-based, async, two-tier archive) |
| JSONL feedback log                                             | `_hermes_feedback.jsonl`, schema in `HERMES_LOOP.md §2`     |
| Health score formula                                           | already aligned across both proposals (§8)                  |
| `archive_index` section with reconstruction guarantee          | §16 Tier B                                                  |
| `schema_evolution` version log (Karpathy format)               | bottom of this file (extend on each schema mutation)        |

**Net:** `template_index.md` contributed operational rigor (vocab, freshness, legal, JSONL substrate, Archive-First protocol) on top of the WIKI_SCHEMA architectural backbone. Architecture preserved. Operational discipline upgraded.

---

## Template-Versionshistorie

Karpathy format. `grep "^## \[" schema/WIKI_SCHEMA.md` → machine-parseable list.

## [2026-04-25 18:00:00] schema_version=1.1.0
- Initial canonical schema — BerlinHackBuena · BaC Hermes-Wiki Engine.
- Liegenschaft root, 7 numbered subfolders, skills.md frontmatter.
- Surgical bullet/row keyed patches.
- DuckDB `wiki_chunks` FTS5 retrieval.
- Inner-loop skill extraction (complexity_score > 5).
- Single-tier `_archive/` folder.

## [2026-04-25 22:00:00] schema_version=1.2.0
- Added §15 per-section metadata annotation (tier / freshness / token_ceiling).
- Added §16 Archive-First two-tier protocol (Tier A bullet, Tier B section + git tag).
- Added §17 pointer to `schema/HERMES_LOOP.md` — outer loop spec finalized.
- Added §18 Decisions & rejected alternatives (provenance vs `template_index.md`).
- New: `schema/HERMES_LOOP.md`, `schema/VOCABULARY.md`, `schema/LEGAL_MAP.md`.
- Per-event flow updated in `schema/CLAUDE.md` step 7 (JSONL append) and step 10–11 (inner + outer loop).
