from __future__ import annotations

import csv
from pathlib import Path

from app.tools.reconcile import reconcile, render_markdown, write_report

_BANK_HEADER = [
    "id",
    "datum",
    "typ",
    "betrag",
    "kategorie",
    "gegen_name",
    "verwendungszweck",
    "referenz_id",
    "error_types",
]

_INVOICE_HEADER = [
    "id",
    "rechnungsnr",
    "datum",
    "dienstleister_id",
    "dienstleister_firma",
    "empfaenger",
    "netto",
    "mwst",
    "brutto",
    "iban",
    "error_types",
    "filename",
    "month_dir",
]


def _bank_row(
    *,
    tx_id: str,
    datum: str = "2024-01-10",
    typ: str = "DEBIT",
    betrag: str = "100.00",
    kategorie: str = "dienstleister",
    gegen_name: str = "Mueller GmbH",
    verwendungszweck: str = "Rechnung",
    referenz_id: str = "",
    error_types: str = "",
) -> list[str]:
    return [
        tx_id,
        datum,
        typ,
        betrag,
        kategorie,
        gegen_name,
        verwendungszweck,
        referenz_id,
        error_types,
    ]


def _invoice_row(
    *,
    inv_id: str,
    datum: str = "2024-01-05",
    dl_id: str = "DL-001",
    brutto: str = "100.00",
    iban: str = "DE00",
    error_types: str = "",
) -> list[str]:
    return [
        inv_id,
        f"R-{inv_id}",
        datum,
        dl_id,
        "Mueller GmbH",
        "Verwalter",
        "84.03",
        "15.97",
        brutto,
        iban,
        error_types,
        f"{datum.replace('-', '')}_{dl_id}_{inv_id}.pdf",
        datum[:7],
    ]


def _write_bank(path: Path, rows: list[list[str]]) -> Path:
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(_BANK_HEADER)
        w.writerows(rows)
    return path


def _write_invoices(path: Path, rows: list[list[str]]) -> Path:
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(_INVOICE_HEADER)
        w.writerows(rows)
    return path


def test_clean_match_has_no_anomalies(tmp_path: Path) -> None:
    bank = _write_bank(
        tmp_path / "bank.csv",
        [_bank_row(tx_id="TX-1", referenz_id="INV-001")],
    )
    invoices = _write_invoices(tmp_path / "inv.csv", [_invoice_row(inv_id="INV-001")])

    report = reconcile(bank_csv=bank, invoice_csvs=[invoices])

    assert report.anomalies == []
    assert report.matched == 1
    assert report.total_bank == 1
    assert report.total_invoices == 1


def test_missing_bank_tx_for_invoice(tmp_path: Path) -> None:
    bank = _write_bank(tmp_path / "bank.csv", [])
    invoices = _write_invoices(tmp_path / "inv.csv", [_invoice_row(inv_id="INV-009")])

    report = reconcile(bank_csv=bank, invoice_csvs=[invoices])

    assert len(report.by_kind("missing_bank_tx")) == 1
    assert report.by_kind("missing_bank_tx")[0].refs["invoice_id"] == "INV-009"


def test_orphan_bank_ref_unknown_invoice(tmp_path: Path) -> None:
    bank = _write_bank(
        tmp_path / "bank.csv",
        [_bank_row(tx_id="TX-1", referenz_id="INV-999")],
    )
    invoices = _write_invoices(tmp_path / "inv.csv", [_invoice_row(inv_id="INV-001")])

    report = reconcile(bank_csv=bank, invoice_csvs=[invoices])

    orphans = report.by_kind("orphan_bank_ref")
    assert len(orphans) == 1
    assert orphans[0].refs["invoice_id"] == "INV-999"


def test_amount_mismatch(tmp_path: Path) -> None:
    bank = _write_bank(
        tmp_path / "bank.csv",
        [_bank_row(tx_id="TX-1", referenz_id="INV-001", betrag="120.00")],
    )
    invoices = _write_invoices(
        tmp_path / "inv.csv",
        [_invoice_row(inv_id="INV-001", brutto="100.00")],
    )

    report = reconcile(bank_csv=bank, invoice_csvs=[invoices])

    mismatches = report.by_kind("amount_mismatch")
    assert len(mismatches) == 1
    assert mismatches[0].refs["delta"] == "20.00"


def test_duplicate_bank_ref(tmp_path: Path) -> None:
    bank = _write_bank(
        tmp_path / "bank.csv",
        [
            _bank_row(tx_id="TX-1", referenz_id="INV-001", betrag="100.00"),
            _bank_row(tx_id="TX-2", referenz_id="INV-001", betrag="100.00"),
        ],
    )
    invoices = _write_invoices(tmp_path / "inv.csv", [_invoice_row(inv_id="INV-001")])

    report = reconcile(bank_csv=bank, invoice_csvs=[invoices])

    dups = report.by_kind("duplicate_bank_ref")
    assert len(dups) == 1
    assert dups[0].refs["tx_ids"] == "TX-1,TX-2"


def test_seeded_error_types_pass_through(tmp_path: Path) -> None:
    bank = _write_bank(
        tmp_path / "bank.csv",
        [_bank_row(tx_id="TX-1", referenz_id="INV-001", error_types="wrong_iban")],
    )
    invoices = _write_invoices(
        tmp_path / "inv.csv",
        [_invoice_row(inv_id="INV-001", error_types="missing_iban")],
    )

    report = reconcile(bank_csv=bank, invoice_csvs=[invoices])

    assert any(a.kind == "seeded_bank_error" for a in report.anomalies)
    assert any(a.kind == "seeded_invoice_error" for a in report.anomalies)


def test_render_markdown_contains_summary(tmp_path: Path) -> None:
    bank = _write_bank(
        tmp_path / "bank.csv",
        [_bank_row(tx_id="TX-1", referenz_id="INV-001")],
    )
    invoices = _write_invoices(tmp_path / "inv.csv", [_invoice_row(inv_id="INV-001")])
    report = reconcile(bank_csv=bank, invoice_csvs=[invoices])

    md = render_markdown(report)

    assert "## Summary" in md
    assert "matched 1:1: 1" in md
    assert md.endswith("\n")


def test_write_report_writes_to_output_and_wiki(tmp_path: Path) -> None:
    bank = _write_bank(tmp_path / "bank.csv", [])
    invoices = _write_invoices(tmp_path / "inv.csv", [_invoice_row(inv_id="INV-001")])
    report = reconcile(bank_csv=bank, invoice_csvs=[invoices])

    output = tmp_path / "out" / "reconciliation.md"
    wiki = tmp_path / "wiki" / "LIE-001" / "05_finances" / "reconciliation.md"
    write_report(report, output_path=output, wiki_path=wiki)

    assert output.is_file()
    assert wiki.is_file()
    assert output.read_text(encoding="utf-8") == wiki.read_text(encoding="utf-8")
    assert "missing_bank_tx" in output.read_text(encoding="utf-8")
