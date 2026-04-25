---
name: wiki-controlled-vocabulary
description: Single source of truth for all controlled-vocabulary values used in keyed bullets, table rows, and frontmatter across the BaC wiki. Patcher and Linter validate every keyed value against this file before emitting a PatchPlan. Unknown value → conflict to `_pending_review.md`, drop op. Append-only — values are never removed (would break historical entries). Read on every Patcher and Linter invocation.
---

# Controlled Vocabulary — Single Source of Truth

Every keyed bullet/row value MUST validate against this file. Patcher and Linter reject unknown values → `_pending_review.md` entry, drop op.

**Append-only.** Removing a value breaks historical entries. New values added via outer-loop schema proposal route only (see `HERMES_LOOP.md §4`).

---

## Risk levels (sections: `physical_infrastructure`, `open_issues`)

`niedrig` | `mittel` | `hoch` | `kritisch`

## Issue priority (sections: `open_issues`, `active_critical_issues`)

| Symbol | Meaning   | SLA          |
|--------|-----------|--------------|
| `🔴`   | Sofort    | ≤ 48 h       |
| `🟡`   | Dringend  | ≤ 14 d       |
| `🟢`   | Geplant   | scheduled    |

## Issue lifecycle (sections: `open_issues`)

`offen` → `zugewiesen` → `in_progress` → `gelöst` → `archiviert`

**Pruning:** status=`gelöst` AND `closed_at > 60d ago` → Archive-First Tier A → row removed.

## Unit status (sections: `unit_register`, `tenancy_snapshot`)

`vermietet` | `leer` | `leerstehend` | `Eigenbedarf` | `Renovierung`

- `leer` = vacant short-term (between tenants, < 90 d).
- `leerstehend` = vacant long-term (≥ 90 d, may indicate structural issue).

## Payment status (sections: `tenancy_snapshot`, payment_history)

`pünktlich` | `verspätet_<N>d` | `ausstehend` | `Widerspruch`

- `verspätet_<N>d` — replace `<N>` with integer days late (e.g. `verspätet_14d`).

## Event type (sections: `recent_events`, `07_timeline.md`)

`email` | `letter` | `invoice` | `bank` | `event` | `inspection` | `legal` | `voicenote` | `slack` | `whatsapp` | `manual`

## Energieausweis class (frontmatter / `core_metadata`)

`A+` | `A` | `B` | `C` | `D` | `E` | `F` | `G` | `H`

## Building type (`core_metadata`)

`Vorderhaus` | `Seitenflügel` | `Hinterhaus` | `Einzelgebäude` | `Gewerbe` | `Mischnutzung`

## Heating fuel (`physical_infrastructure`)

`Gas` | `Öl` | `Fernwärme` | `Wärmepumpe` | `Pellet` | `Strom` | `Solar+Backup`

## Pipe material (`physical_infrastructure`)

`Kupfer` | `Stahl` | `Kunststoff` | `Verbund` | `Blei`

`Blei` MUST trigger an open_issues entry (priority `🟡`, replacement obligation per Trinkwasserverordnung).

## Confidence labels (skills.md, signal classifier)

| Range        | Label         |
|--------------|---------------|
| 0.90 – 1.00  | `verified`    |
| 0.70 – 0.89  | `confident`   |
| 0.50 – 0.69  | `tentative`   |
| 0.30 – 0.49  | `weak`        |
| < 0.30       | `do_not_use`  |

`do_not_use` requires PM review before any agent action.

## Signal class (Signal Filter output)

`HIGH` | `MEDIUM` | `LOW` | `NOISE`

- `HIGH` and `MEDIUM` produce a PatchPlan.
- `LOW` logs JSONL with `retrieval_success=null`, no patch.
- `NOISE` logs and discards.

## Tier (per-section metadata, see `WIKI_SCHEMA.md §15`)

`0` (critical, retrieve always) | `1` (dynamic, ~80% of queries) | `2` (static, deep/historical)

## Freshness units (per-section metadata)

`<N>d` | `<N>w` | `<N>m` | `<N>y`

- Examples: `7d`, `2w`, `90d`, `1y`.

## Patcher op names (`PatchPlan.ops[].op`)

`upsert_bullet` | `delete_bullet` | `upsert_row` | `delete_row` | `prepend_row` | `prune_ring` | `upsert_footnote` | `gc_footnotes` | `update_state`

## JSONL event kinds (`_hermes_feedback.jsonl`)

`ingest` | `skill_extracted` | `correction` | `schema_proposal` | `schema_approved` | `schema_rejected`

---

## Empty-state lines (canonical)

When a section has no rows/bullets, write the canonical empty-state line so retrieval still hits a deterministic answer:

| Section | Empty-state line |
|---|---|
| `Open Issues` (any) | `_Keine offenen Punkte. Geprüft: YYYY-MM-DD_` |
| `active_critical_issues` | `_Keine kritischen Punkte. Geprüft: YYYY-MM-DD_` |
| `Recent Events` | `_Keine Ereignisse in den letzten 60 Tagen._` |
| `Procedural Memory` | `_Keine Skills extrahiert._` |
| `Aktive Sonderumlagen` | `_Keine aktiven Sonderumlagen._` |
| `Offene Beschlüsse` | `_Keine offenen Beschlüsse._` |
| `Provenance` (always non-empty if any fact cited) | n/a |

Patcher writes the empty-state line on section initialization. Removes it on first real upsert. Restores it after the last delete brings the section back to zero.

---

## Validating against this file

```python
# pseudocode — Patcher pre-flight
allowed = parse_vocabulary("schema/VOCABULARY.md")
for op in plan.ops:
    if op.field in allowed and op.value not in allowed[op.field]:
        defer_to_pending_review(op, reason=f"unknown vocab: {op.field}={op.value!r}")
        plan.ops.remove(op)
```

The Linter watches `git log` for `correction` events touching values outside this file → enqueues `schema_proposal` to add the value (outer-loop route, append-only path).
