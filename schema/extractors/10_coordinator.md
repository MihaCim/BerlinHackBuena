# 10 — Daily Coordinator

Input: JSON outputs from manifest, stammdaten, all index extractors, and all per-file extractors for one `day-NN` package.

Goal: produce ONE `PatchPlan` for the Patcher, plus a review queue. You do not re-extract source text. You only merge, deduplicate, link, and validate.

## Tasks

1. Validate package counts (manifest expected vs observed).
2. Deduplicate source records by `source_id`.
3. Link invoices to bank transactions via `reference_id`, `invoice_number`, or amount+date+vendor match.
4. Link emails/letters to issues, invoices, owners, tenants, vendors, properties.
5. Resolve every op's target entities through the stammdaten registry. Unresolved → drop op, raise `review_item`.
6. Conflict scan: for each `upsert_bullet` / `upsert_row`, look up the existing keyed line via `query_wiki(entity_id)` over the `wiki_chunks` DuckDB index. Contradicting fact → drop op, append to `_pending_review.md` (output as `review_item`).
7. Compose ring-buffer ops: `prepend_row` on `Recent Events` and `prune_ring(max=50)`.
8. Compose footnote ops: every new source ID gets `upsert_footnote` on every file it appears in. Emit `gc_footnotes` if any source becomes unreferenced after deletes.
9. State updates: `update_state` for `open_issues_count`, `overdue_invoices_count`, `pending_review_count` when their counts change.
10. Forbid: ops on sections not in the section vocabulary, ops on paths not in Path Resolution, full-page rewrites, writes past `# Human Notes`, ops from `noise` sources, ops on high-level pages from low-confidence facts.

## Return

Exactly the PatchPlan shape from `schema/CLAUDE.md`:

```json
{
  "property_id": "",
  "source_ids": [],
  "event_type": "daily_delta",
  "package": {
    "day_index": null,
    "content_date": null,
    "package_path": "",
    "count_validation": {
      "emails_expected": 0,
      "emails_observed": 0,
      "invoices_expected": 0,
      "invoices_observed": 0,
      "bank_transactions_expected": 0,
      "bank_transactions_observed": 0,
      "mismatches": []
    }
  },
  "cross_source_links": [
    {
      "link_type": "invoice_paid_by_transaction|email_mentions_invoice|email_updates_issue|source_mentions_entity|possible_duplicate",
      "source_ids": [],
      "confidence": "low|medium|high"
    }
  ],
  "ops": [
    {
      "file": "",
      "section": "",
      "op": "upsert_bullet|delete_bullet|upsert_row|delete_row|prepend_row|prune_ring|upsert_footnote|gc_footnotes|update_state",
      "key": null,
      "content": null,
      "field": null,
      "value": null
    }
  ],
  "review_items": [
    {
      "review_type": "entity_match|property_match|contradiction|risky_update|missing_source|data_quality",
      "title": "",
      "description": "",
      "source_ids": [],
      "severity": "low|medium|high"
    }
  ],
  "complexity_score": 0,
  "skill_candidate": false
}
```
