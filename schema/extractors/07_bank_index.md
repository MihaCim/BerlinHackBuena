# 07 — Bank Index Extractor

Input: `bank_index.csv`.

Columns: `id, datum, typ, betrag, kategorie, gegen_name, verwendungszweck, referenz_id, error_types`.

Goal: per-row transactions plus invoice/entity link hints. No ops yet (raw bank delta extractor and coordinator emit ops after reconciliation).

For each row:
- `TX-*` as `transaction_id`
- parse `betrag` as positive decimal; preserve direction from `typ`
- `referenz_id` → strong link to invoice or entity
- extract invoice numbers, names, IBAN tokens from `verwendungszweck`
- `gegen_name` is not automatically owner/tenant/service_provider without `referenz_id`, IBAN match, or master_data support

Return:

```json
{
  "extractor": "bank_index",
  "source": { "source_path": "", "source_type": "index_csv" },
  "transactions": [
    {
      "transaction_id": "",
      "booking_date": null,
      "type": "DEBIT|CREDIT|unknown",
      "amount": null,
      "currency": "EUR",
      "category": "",
      "counterparty_name": "",
      "purpose": "",
      "reference_id": null,
      "candidate_entity_ids": [],
      "candidate_invoice_ids": [],
      "signal_class": "financial_update",
      "confidence": "low|medium|high",
      "review_reason": null
    }
  ],
  "warnings": []
}
```
