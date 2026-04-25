# 03 — Email Index Extractor

Input: one `emails_index.csv`.

Columns: `id, datetime, thread_id, direction, from_email, to_email, subject, category, sprache, error_types, filename, month_dir`.

Goal: produce per-row source records and entity hints for the body extractor. No ops yet — body extractor emits ops.

For each row:
- preserve `EMAIL-*` as `source_id`
- expected source path: `emails/{month_dir}/{filename}`
- normalized path: `normalize/eml/{month_dir}/{source_id}.md`
- match `from_email` / `to_email` against stammdaten registry → candidate entity IDs
- pre-classify subject only (greetings, newsletters, autoreplies → `noise` or `reference_only`)
- flag rows with `error_types`

Return:

```json
{
  "extractor": "emails_index",
  "source": { "source_path": "", "source_type": "index_csv" },
  "email_sources": [
    {
      "source_id": "",
      "thread_id": "",
      "datetime": null,
      "direction": "in|out",
      "from_email": "",
      "to_email": "",
      "subject": "",
      "category": "",
      "language": "",
      "expected_eml_path": "",
      "normalized_source_path": "",
      "candidate_entity_ids": [],
      "candidate_signal_class": "",
      "confidence": "low|medium|high",
      "review_reason": null
    }
  ],
  "thread_groups": [
    {
      "thread_id": "",
      "source_ids": [],
      "first_datetime": null,
      "last_datetime": null
    }
  ],
  "warnings": []
}
```
