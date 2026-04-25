# 08 — Sparkasse Delta Extractor

Input: semicolon-separated `kontoauszug_delta.csv` (raw bank export).

Columns: `Auftragskonto, Buchungstag, Valutadatum, Buchungstext, Verwendungszweck, Glaeubiger-ID, Mandatsreferenz, Kundenreferenz (End-to-End), Sammlerreferenz, Lastschrift Ursprungsbetrag, Auslagenersatz Ruecklastschrift, Beguenstigter/Zahlungspflichtiger, Kontonummer/IBAN, BIC (SWIFT-Code), Betrag, Waehrung, Info`.

## Parsing

- dates: `DD.MM.YYYY`
- amounts: comma decimal, signed (negative = debit)
- extract `TX-*` from `Kundenreferenz (End-to-End)`
- extract invoice numbers from `Verwendungszweck`
- balance from `Info` is metadata, not a fact

Goal: normalized transaction lines and reconciliation against `bank_index.csv` if provided. No wiki ops directly — coordinator emits ops after invoice ↔ transaction link.

## Return

```json
{
  "extractor": "kontoauszug_delta",
  "source": {
    "source_path": "",
    "normalized_source_path": "",
    "source_type": "bank_transaction"
  },
  "lines": [
    {
      "transaction_id": null,
      "account_iban": "",
      "booking_date": null,
      "value_date": null,
      "booking_text": "",
      "purpose": "",
      "creditor_id": null,
      "mandate_reference": null,
      "end_to_end_reference": null,
      "counterparty_name": "",
      "counterparty_iban": "",
      "bic": "",
      "signed_amount": null,
      "direction": "DEBIT|CREDIT|unknown",
      "currency": "EUR",
      "balance_hint": null,
      "invoice_number_candidates": [],
      "candidate_invoice_ids": [],
      "confidence": "low|medium|high"
    }
  ],
  "validation": {
    "matches_bank_index": null,
    "mismatches": []
  },
  "review_items": []
}
```
