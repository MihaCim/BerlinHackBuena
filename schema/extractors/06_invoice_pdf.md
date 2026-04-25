# 06 — Invoice PDF Extractor

Input: normalized invoice markdown generated from a PDF with pypdf text extraction. Optional: row from `rechnungen_index.csv`, vendor record from stammdaten.

Goal: produce a PatchPlan fragment for the invoice page, vendor page, and any HAUS/unit timeline. Emit financial facts. Do NOT emit context-changing ops for routine recurring billing.

## Extract

invoice_number, invoice_date, vendor (id, name, address, IBAN), recipient, line_items, net/vat/gross, due_date, service_period, work_category, property/building/unit references, issue references.

## Validate

Against index row: invoice_number, date, vendor, IBAN, gross. Mismatches → `review_item`.

## Op Rules

- invoice page: `upsert_row` on `output/LIE-XXX/05_finances/invoices/<YYYY-MM>/INV-XXXXX.md` sections `Invoice` and `Line Items` (one row per line item, key = line index)
- vendor page: `upsert_row` on `DL-XXX.md` `Recent Invoices`, key = `INV-XXXXX`
- if invoice references a HAUS or unit → `prepend_row` on `HAUS/index.md` `Recent Events` (signal_class = `financial_update`)
- if work changes durable building state (installation, replacement, completed repair, inspection result) → emit a `fact` flagged for `physical.md` and a `review_item` (do NOT auto-patch physical.md)
- footnote upserts on every patched file

## Return

```json
{
  "extractor": "invoice_pdf",
  "source": {
    "source_id": "",
    "source_path": "",
    "normalized_source_path": "",
    "source_type": "invoice",
    "document_date": null,
    "title": "",
    "confidence": "low|medium|high"
  },
  "invoice": {
    "invoice_number": "",
    "vendor_id": null,
    "vendor_name": "",
    "vendor_iban": null,
    "recipient": "",
    "service_period": null,
    "due_date": null,
    "net_amount": null,
    "vat_amount": null,
    "gross_amount": null,
    "currency": "EUR",
    "line_items": [
      { "description": "", "quantity": null, "unit_price": null, "net_amount": null, "gross_amount": null }
    ]
  },
  "candidate_links": {
    "property_ids": [],
    "building_ids": [],
    "unit_ids": [],
    "issue_ids": [],
    "bank_transaction_ids": []
  },
  "facts": [],
  "validation": {
    "matches_index": true,
    "mismatches": []
  },
  "ops": [],
  "summary": {
    "short_summary": "",
    "signal_class": "financial_update"
  },
  "review_items": []
}
```
