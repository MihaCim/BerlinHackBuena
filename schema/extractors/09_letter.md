# 09 — Letter Extractor

Input: extracted text + metadata for one letter under `data/briefe/<YYYY-MM>/...`.

Treat like email but with sender/recipient parsed from the letterhead and address block.

Goal: PatchPlan fragment for issues, contact updates, or correspondence summaries. Same op rules as `04_eml.md`.

- `LTR-*` source IDs
- normalized path: `normalize/letter/<YYYY-MM>/LTR-XXXX.md`
- `direction` based on letter sender vs recipient

Return the same JSON shape as `04_eml.md`, with `source_type: "letter"`.
