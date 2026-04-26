# 05 — Invoice Index Extractor

Input: one `rechnungen_index.csv`.

Columns: `id, rechnungsnr, datum, dienstleister_id, dienstleister_firma, empfaenger, netto, mwst, brutto, iban, error_types, filename, month_dir`.

Goal: per-row source records and vendor hints. No ops.

For each row:
- preserve `INV-*` as `source_id`
- preserve `DL-*` if present
- expected pdf path: `rechnungen/{month_dir}/{filename}`
- normalized path: `normalize/pdf/{month_dir}/{source_id}.md`
- parse `netto/mwst/brutto` as decimals
- flag malformed amounts, missing DL-id, duplicate `rechnungsnr`

Return:

```json
{
  "extractor": "rechnungen_index",
  "source": { "source_path": "", "source_type": "index_csv" },
  "invoice_sources": [
    {
      "source_id": "",
      "invoice_number": "",
      "invoice_date": null,
      "vendor_id": null,
      "vendor_name": "",
      "recipient": "",
      "net_amount": null,
      "vat_amount": null,
      "gross_amount": null,
      "iban": "",
      "expected_pdf_path": "",
      "normalized_source_path": "",
      "candidate_signal_class": "financial_update",
      "confidence": "low|medium|high",
      "review_reason": null
    }
  ],
  "warnings": []
}
```
