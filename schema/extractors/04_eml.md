# 04 — Email Body Extractor

Input: one `.eml` (headers + body). Optional: row from `emails_index.csv`, candidate entity IDs from stammdaten.

Goal: produce a PatchPlan fragment plus facts and entity records.

## Parsing

From, To, Cc, Subject, Date, Message-ID, body, attachments. Strip quoted reply text — do not derive new facts from quoted content.

## Resolution

- sender entity: from address → MIE/EIG/DL via stammdaten
- mentioned IDs: validate against stammdaten
- mentioned addresses / unit numbers → resolve to LIE/HAUS/EH

## Domain Cues

- `Sonderumlage, Einspruch, Beschluss, Frist, Mahnung, Klage, Mieterhöhung` → `risk_update`
- `Kaution, Nebenkosten, BKA, Hausgeld` → `financial_update` or `task_update`
- `Heizung, Wasser, Schimmel, Dach, Rohr, Notdienst` → `task_update` (open issue)
- `Rechnung, Zahlung, Überweisung, offen, bezahlt` → `financial_update`
- newsletter / autoreply / FYI / scheduling chatter → `reference_only` or `noise`

## Op Rules

- new open issue on a unit → `upsert_bullet` on `HAUS/index.md` `Open Issues`, key = `EH-XXX`
- any signal that isn't `noise` → `prepend_row` on `HAUS/index.md` `Recent Events`
- tenant communication → `prepend_row` on `MIE-XXX.md` `Contact History`
- owner communication → append entry to `EIG-XXX.md` `Correspondence Summary`
- contact detail change (address, email, phone) → `upsert_row` on the entity `Contact` section, key = field name
- every emitted bullet/row → matching `upsert_footnote` on the same file
- unresolved property/unit → no ops, emit `review_item`

## Return

```json
{
  "extractor": "eml_email",
  "source": {
    "source_id": "",
    "source_path": "",
    "normalized_source_path": "",
    "source_type": "email",
    "document_date": null,
    "title": "",
    "message_id": "",
    "thread_id": null,
    "direction": "in|out",
    "language": null,
    "confidence": "low|medium|high"
  },
  "participants": [
    {
      "role": "from|to|cc",
      "name": "",
      "email": "",
      "entity_id": null,
      "confidence": "low|medium|high"
    }
  ],
  "facts": [
    {
      "subject": "",
      "predicate": "",
      "object": "",
      "candidate_property_id": null,
      "candidate_unit_id": null,
      "confidence": "low|medium|high"
    }
  ],
  "ops": [
    {
      "file": "",
      "section": "",
      "op": "upsert_bullet|upsert_row|prepend_row|upsert_footnote",
      "key": null,
      "content": null,
      "field": null,
      "value": null
    }
  ],
  "summary": {
    "short_summary": "",
    "signal_class": "",
    "why_it_matters": ""
  },
  "review_items": []
}
```
