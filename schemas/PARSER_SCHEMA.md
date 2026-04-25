# Parser Schema

Purpose: describe source families, filename patterns, and classification rules that guide ingestion.

The parser executor must follow this schema for known source families. If a source family is missing, it must skip that family rather than invent paths.

## Source Families

| family | base_path | delta_path | index_file | file_pattern | parser |
|---|---|---|---|---|---|
| master | stammdaten/stammdaten.json |  |  |  | json_master |
| bank | bank/bank_index.csv | bank/bank_index.csv | bank_index.csv |  | csv_bank |
| invoices | rechnungen | rechnungen_index.csv | rechnungen_index.csv | `(?P<date>\d{8})_DL-(?P<vendor>\d{3})_INV-(?P<inv>\d{5})\.pdf$` | invoice_pdf_path |
| invoice_duplicates | rechnungen | rechnungen_index.csv | rechnungen_index.csv | `(?P<date>\d{8})_DL-(?P<vendor>\d{3})_INV-DUP-(?P<inv>\d{5})\.pdf$` | invoice_duplicate_pdf_path |
| letters | briefe |  |  | `(?P<date>\d{8})_(?P<kind>[a-z_]+)_LTR-(?P<num>\d{4})\.pdf$` | letter_pdf_path |
| emails | emails | emails | emails_index.csv | `.*\.eml$` | eml |

## Entity Pattern

```regex
\b(?:EH|EIG|MIE|DL|INV|LTR)-\d{3,5}\b
```

## Email Classification Rules

The first matching category wins.

| category | keywords |
|---|---|
| rechtlich | einspruch, beschluss, kuendigung, kundigung, mahnung, recht, frist |
| mieter/kaution | kaution |
| rechnung | rechnung, invoice, abrechnung |
| schaden | leck, wasserschaden, heizung, aufzug, schimmel, defekt |
| eigentuemer | eigentuemer, eigentumer, sonderumlage, etv |
| noise | newsletter, werbung, angebot |

## Email Score Rules

| label | keywords | boost |
|---|---|---:|
| legal | recht, einspruch, kuendigung, kundigung, frist, mahnung | 0.35 |
| financial | rechnung, kaution, zahlung, sonderumlage, hausgeld | 0.20 |
| operational | heizung, wasser, leck, aufzug, schimmel, notfall | 0.25 |
| noise | noise | -0.30 |

Base email score: `0.35`.
