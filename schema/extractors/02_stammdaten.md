# 02 — Stammdaten Loader

Input: master-data files from `data/stammdaten/` — `eigentuemer.csv`, `mieter.csv`, `einheiten.csv`, `dienstleister.csv`, `stammdaten.json`.

Goal: produce a flat entity registry used by all later extractors for resolution. No wiki ops.

For each row produce one entity record with canonical ID, canonical entity type, source labels, identifiers (email, IBAN, address, phone), and the wiki `page_path` per Path Resolution.

Return:

```json
{
  "extractor": "stammdaten",
  "source": { "source_path": "" },
  "entities": [
    {
      "entity_id": "",
      "entity_type": "liegenschaft|gebaeude|einheit|eigentuemer|mieter|dienstleister",
      "name": "",
      "aliases": [],
      "identifiers": {
        "email": null,
        "iban": null,
        "address": null,
        "phone": null
      },
      "parent_ids": [],
      "page_path": "",
      "source_label": ""
    }
  ],
  "warnings": []
}
```
