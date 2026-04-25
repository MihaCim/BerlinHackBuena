---
name: german-legal-reference-map
description: Mapping of German WEG- and Berlin-specific regulatory obligations to the wiki sections that hold their compliance state. Patcher and Linter use this to encode statutory deadlines and quorum rules without re-deriving them per ingest. Each row maps a regulation to its source paragraph, the wiki section that tracks compliance, and the action the Linter takes when a deadline approaches. Read whenever an ingest involves ETV, Wirtschaftsplan, BKA, Rücklage, Mieterhöhung, or technical inspections.
---

# German Legal Reference Map

WEG- and Berlin-specific obligations encoded so Patcher and Linter need not re-derive them per ingest. Each row maps a regulation to: source, target wiki section, and Linter action.

| # | Obligation | Source | Wiki section | Linter action |
|---|---|---|---|---|
| 1 | Rauchwarnmelderpflicht | §45 Abs. 6 BauO Bln | HAUS · `physical_infrastructure` | annual nachweis-check, log to `recent_events` |
| 2 | ETV Einladungsfrist 21 Tage | §24 Abs. 4 WEGesetz | LIE · `weg_compliance` | block any "Beschluss" claim if `etv_einladung_datum + 21d > etv_datum` |
| 3 | Beschlussfähigkeit > 50% MEA | §25 Abs. 3 WEGesetz | LIE · `weg_compliance` | reject Beschluss recording if quorum < 50% MEA |
| 4 | Rücklage-Adequacy-Formel | §19 Abs. 2 WEGesetz | LIE · `financial_snapshot` + `weg_compliance` | nightly recompute, set ✅ / ⚠️ / 🔴 verdict |
| 5 | Verwaltervertrag Laufzeit | §26 WEGesetz | LIE · `legal_documents` | flag if expiry < 6 months |
| 6 | Aufzug TÜV-Pflicht | §14 BetrSichV | HAUS · `physical_infrastructure` | track `nächste-Pflichtprüfung`, alert at -30 d |
| 7 | E-Check Elektroanlage | §5 DGUV V3 | HAUS · `physical_infrastructure` | 4-year cycle, alert at 3.5 y |
| 8 | Heizkostenabrechnung | §7 HeizkostenV | LIE · `financial_snapshot` | annual cycle, link to BKA |
| 9 | Mieterhöhung Frist | §558 BGB | HAUS · `tenancy_snapshot` | enforce 15-month gap rule, Kappungsgrenze 20% / 15% (Berlin) |
| 10 | Kaution-Verzinsung | §551 Abs. 3 BGB | MIE-XX.md · Tenancy | annual interest accrual log |
| 11 | Energieausweis-Pflicht | §80 GEG | LIE · `core_metadata` + `legal_documents` | flag at 9.5 y for renewal |
| 12 | Trinkwasser Legionellen-Prüfung | §14 TrinkwV | HAUS · `physical_infrastructure` | 3-year cycle, mandatory if ≥ 3 units |
| 13 | DSGVO Personendaten | Art. 5–17 DSGVO | global | enforce minimization in JSONL writes; retention rules per category |
| 14 | Brandschutzklappen-Wartung | DIN 18017-3 / MLAR | HAUS · `physical_infrastructure` | annual cycle |
| 15 | Beirat-Wahl Turnus | §29 WEGesetz | LIE · `weg_compliance` | flag at end of Beirat term |

---

## Rücklage-Adequacy-Formel (load-bearing — referenced by §4)

```
Target = max(12 €/qm/Jahr, Gebäudealter_Jahre × 0.9 €/qm/Jahr) × qm_total
```

### Verdict thresholds

| Bestand vs Target           | Verdict          |
|-----------------------------|------------------|
| `bestand ≥ target`          | ✅ ausreichend   |
| `0.7·target ≤ b < target`   | ⚠️ knapp         |
| `bestand < 0.7·target`      | 🔴 unzureichend |

Linter writes the verdict into `## Instandhaltungsrücklage — Adequacy-Check` of `financial_snapshot` on every nightly run.

---

## ETV invitation gate (referenced by §2 + §3)

Linter check:

```
IF etv_datum - etv_einladung_datum < 21 days:
    write conflict to _pending_review.md
    block all "Beschluss" recordings tied to this ETV
    DO NOT remove existing Beschluss bullets retroactively
```

Conflict resolution: PM either confirms an emergency-ETV exception or invalidates the ETV's resolutions.

---

## Mieterhöhung gate (referenced by §9)

Linter check before recording any rent-increase event:

```
last_increase_date = MIE-XX.md → "Mieterhöhung" history
IF (occurred_at - last_increase_date) < 15 months:
    reject op, write conflict to _pending_review.md
IF cap_violated(berlin_kappungsgrenze=15%, federal=20%):
    reject op, write conflict
```

Berlin Kappungsgrenze (15%) applies via `Mietenbegrenzungsverordnung`. Verified via building's `PLZ` against the active municipal list (cached in `schema/berlin_kappung_plz.csv`, refresh annually).

---

## Adding new obligations

Same as `VOCABULARY.md`: append-only. New rows added via outer-loop schema proposal route only (`HERMES_LOOP.md §4`). Removing a row requires Tier B Archive-First with git tag.

---

## Linter daily run order

1. §4 Rücklage adequacy recompute (cheap, deterministic).
2. §5 Verwaltervertrag expiry scan.
3. §6 Aufzug TÜV deadline scan.
4. §7 E-Check cycle scan.
5. §11 Energieausweis renewal scan.
6. §12 Legionellen cycle scan.
7. §15 Beirat term scan.

Each scan emits at most one `🟡` open_issues bullet per affected entity per scan. Idempotent: repeated runs do not duplicate bullets (upsert keyed by obligation + entity).
