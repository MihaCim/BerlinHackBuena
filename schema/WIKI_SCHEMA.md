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
| ID | Mieter | Status |
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
