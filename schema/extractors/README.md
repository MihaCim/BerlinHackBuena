# Extractor Prompts

One prompt per file. Authoritative contract: `schema/CLAUDE.md` and `schema/WIKI_SCHEMA.md`.

## Pipeline

```
NORMALIZE → CLASSIFY → RESOLVE ENTITIES → LOCATE SECTIONS → EXTRACT (these prompts) → CONFLICT SCAN → APPLY → REINDEX
```

Index extractors (manifest, *_index.csv) produce source records and routing data. File-level extractors (.eml, invoice PDF, letter PDF, raw bank delta) emit PatchPlan op fragments. Coordinator merges fragments into one PatchPlan per `day-NN`.

## How to invoke

For each extractor call concatenate:

1. `00_shared_rules.md`
2. the specific extractor file
3. file content + metadata (resolved entity IDs from the master-data registry if available)

One call per source file or per homogeneous table.

## Files

| # | File | Input | Emits ops? |
|---|---|---|---|
| 00 | `00_shared_rules.md` | — (prepended to every call) | — |
| 01 | `01_manifest.md` | `day-NN/incremental_manifest.json` | no |
| 02 | `02_master_data.md` | `data/stammdaten/*` | no |
| 03 | `03_emails_index.md` | `day-NN/emails_index.csv` | no |
| 04 | `04_eml.md` | `day-NN/emails/<YYYY-MM>/*.eml` | yes |
| 05 | `05_invoices_index.md` | `day-NN/rechnungen_index.csv` | no |
| 06 | `06_invoice_pdf.md` | `day-NN/rechnungen/<YYYY-MM>/*.pdf` | yes |
| 07 | `07_bank_index.md` | `day-NN/bank/bank_index.csv` | no |
| 08 | `08_kontoauszug.md` | `day-NN/bank/kontoauszug_delta.csv` | no |
| 09 | `09_letter.md` | `data/briefe/<YYYY-MM>/*.pdf` | yes |
| 10 | `10_coordinator.md` | all extractor outputs for one `day-NN` | yes (final PatchPlan) |
