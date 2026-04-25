# 01 — Manifest Extractor

Input: one `day-NN/incremental_manifest.json`.

Goal: report package counts and metadata. No wiki ops.

Return:

```json
{
  "extractor": "manifest",
  "source": {
    "source_path": "",
    "source_type": "manifest"
  },
  "package": {
    "schema_version": null,
    "day_index": null,
    "content_date": null,
    "seed": null,
    "difficulty": null,
    "expected_counts": {
      "emails": 0,
      "invoices": 0,
      "bank_transactions": 0
    },
    "stammdaten_relative": null,
    "note": null
  },
  "warnings": []
}
```
