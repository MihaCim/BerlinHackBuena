# Extractor Prompts

One prompt per file. Authoritative contract: `schema/CLAUDE.md` and `schema/WIKI_SCHEMA.md`.

## Pipeline

```
NORMALIZE → CLASSIFY → RESOLVE ENTITIES → LOCATE SECTIONS → EXTRACT (these prompts) → CONFLICT SCAN → APPLY → REINDEX
```

Index extractors (manifest, *_index.csv) produce source records and routing data. File-level extractors consume normalized markdown generated under `normalize/`, then emit PatchPlan op fragments. Coordinator merges fragments into one PatchPlan per `day-NN`.

## How to invoke

For each extractor call concatenate:

1. `00_shared_rules.md`
2. the specific extractor file
3. normalized markdown content + metadata (resolved entity IDs from stammdaten if available)

One call per source file or per homogeneous table.

## Files

| # | File | Input | Emits ops? |
|---|---|---|---|
| 00 | `00_shared_rules.md` | — (prepended to every call) | — |
| 01 | `01_manifest.md` | `day-NN/incremental_manifest.json` | no |
| 02 | `02_stammdaten.md` | `normalize/base/stammdaten/*` | no |
| 03 | `03_emails_index.md` | `day-NN/emails_index.csv` | no |
| 04 | `04_eml.md` | `normalize/**/emails/<YYYY-MM>/*.md` | yes |
| 05 | `05_rechnungen_index.md` | `day-NN/rechnungen_index.csv` | no |
| 06 | `06_invoice_pdf.md` | `normalize/**/rechnungen/<YYYY-MM>/*.md` | yes |
| 07 | `07_bank_index.md` | `day-NN/bank/bank_index.csv` | no |
| 08 | `08_kontoauszug.md` | `day-NN/bank/kontoauszug_delta.csv` | no |
| 09 | `09_letter.md` | `normalize/**/briefe/<YYYY-MM>/*.md` | yes |
| 10 | `10_coordinator.md` | all extractor outputs for one `day-NN` | yes (final PatchPlan) |
