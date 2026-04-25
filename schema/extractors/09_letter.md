# 09 — Letter Extractor

Input: normalized letter markdown generated from a PDF under `normalize/**/briefe/<YYYY-MM>/...`.

Treat like email but with sender/recipient parsed from the letterhead and address block.

Goal: PatchPlan fragment for issues, contact updates, or correspondence summaries. Same op rules as `04_eml.md`.

- `LTR-*` source IDs
- normalized path: `normalize/base/briefe/<YYYY-MM>/<filename-with-md-extension>` or `normalize/incremental/day-NN/briefe/<YYYY-MM>/<filename-with-md-extension>`
- `direction` based on letter sender vs recipient

Return the same JSON shape as `04_eml.md`, with `source_type: "letter"`.
