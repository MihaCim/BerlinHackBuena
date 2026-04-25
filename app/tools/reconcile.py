from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import structlog

from app.core.config import get_settings
from app.services.patcher.atomic import atomic_write_text

log = structlog.get_logger(__name__)

_AMOUNT_TOLERANCE = Decimal("0.01")


@dataclass(frozen=True)
class Anomaly:
    kind: str
    detail: str
    refs: dict[str, str]


@dataclass(frozen=True)
class ReconciliationReport:
    anomalies: list[Anomaly]
    counts: dict[str, int]
    total_bank: int
    total_invoices: int
    matched: int

    def by_kind(self, kind: str) -> list[Anomaly]:
        return [a for a in self.anomalies if a.kind == kind]


@dataclass
class _BankTx:
    id: str
    datum: str
    typ: str
    betrag: Decimal | None
    kategorie: str
    referenz_id: str
    error_types: str
    raw: dict[str, str] = field(default_factory=dict)


@dataclass
class _Invoice:
    id: str
    datum: str
    dl_id: str
    brutto: Decimal | None
    iban: str
    error_types: str
    raw: dict[str, str] = field(default_factory=dict)


def reconcile(
    *,
    bank_csv: Path,
    invoice_csvs: Iterable[Path],
) -> ReconciliationReport:
    bank = list(_load_bank(bank_csv))
    invoices = list(_load_invoices(invoice_csvs))

    by_ref: dict[str, list[_BankTx]] = defaultdict(list)
    for tx in bank:
        if tx.referenz_id:
            by_ref[tx.referenz_id].append(tx)
    invoice_ids = {inv.id for inv in invoices}

    anomalies: list[Anomaly] = []
    anomalies.extend(_check_duplicates(by_ref, invoice_ids))
    anomalies.extend(_check_orphan_bank_refs(by_ref, invoice_ids))
    anomalies.extend(_check_invoice_match(invoices, by_ref))
    anomalies.extend(_check_seeded_errors(bank, invoices))

    counts: Counter[str] = Counter(a.kind for a in anomalies)
    matched = sum(1 for inv in invoices if len(by_ref.get(inv.id, [])) == 1)
    return ReconciliationReport(
        anomalies=anomalies,
        counts=dict(counts),
        total_bank=len(bank),
        total_invoices=len(invoices),
        matched=matched,
    )


def _check_duplicates(
    by_ref: dict[str, list[_BankTx]],
    invoice_ids: set[str],
) -> list[Anomaly]:
    out: list[Anomaly] = []
    for ref, txs in by_ref.items():
        if len(txs) > 1 and ref in invoice_ids:
            out.append(
                Anomaly(
                    kind="duplicate_bank_ref",
                    detail=f"{len(txs)} bank transactions share referenz_id {ref}",
                    refs={"invoice_id": ref, "tx_ids": ",".join(t.id for t in txs)},
                )
            )
    return out


def _check_orphan_bank_refs(
    by_ref: dict[str, list[_BankTx]],
    invoice_ids: set[str],
) -> list[Anomaly]:
    out: list[Anomaly] = []
    for ref, txs in by_ref.items():
        if ref.startswith("INV-") and ref not in invoice_ids:
            out.append(
                Anomaly(
                    kind="orphan_bank_ref",
                    detail=f"bank tx references unknown invoice {ref}",
                    refs={"invoice_id": ref, "tx_ids": ",".join(t.id for t in txs)},
                )
            )
    return out


def _check_invoice_match(
    invoices: list[_Invoice],
    by_ref: dict[str, list[_BankTx]],
) -> list[Anomaly]:
    out: list[Anomaly] = []
    for inv in invoices:
        txs = by_ref.get(inv.id, [])
        if not txs:
            out.append(
                Anomaly(
                    kind="missing_bank_tx",
                    detail=f"invoice {inv.id} has no matching bank tx",
                    refs={"invoice_id": inv.id, "dl_id": inv.dl_id, "datum": inv.datum},
                )
            )
            continue
        if inv.brutto is None:
            continue
        out.extend(_amount_mismatches(inv, txs))
    return out


def _amount_mismatches(inv: _Invoice, txs: list[_BankTx]) -> list[Anomaly]:
    out: list[Anomaly] = []
    if inv.brutto is None:
        return out
    for tx in txs:
        if tx.betrag is None:
            continue
        delta = abs(tx.betrag - inv.brutto)
        if delta > _AMOUNT_TOLERANCE:
            out.append(
                Anomaly(
                    kind="amount_mismatch",
                    detail=(
                        f"bank {tx.id} {tx.betrag} EUR vs invoice {inv.id} "
                        f"{inv.brutto} EUR (delta {delta})"
                    ),
                    refs={"tx_id": tx.id, "invoice_id": inv.id, "delta": str(delta)},
                )
            )
    return out


def _check_seeded_errors(bank: list[_BankTx], invoices: list[_Invoice]) -> list[Anomaly]:
    out: list[Anomaly] = []
    for tx in bank:
        if tx.error_types:
            out.append(
                Anomaly(
                    kind="seeded_bank_error",
                    detail=tx.error_types,
                    refs={"tx_id": tx.id, "ref": tx.referenz_id},
                )
            )
    for inv in invoices:
        if inv.error_types:
            out.append(
                Anomaly(
                    kind="seeded_invoice_error",
                    detail=inv.error_types,
                    refs={"invoice_id": inv.id, "dl_id": inv.dl_id},
                )
            )
    return out


def _load_bank(path: Path) -> Iterable[_BankTx]:
    if not path.is_file():
        return
    with path.open("r", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            yield _BankTx(
                id=row.get("id", ""),
                datum=row.get("datum", ""),
                typ=row.get("typ", ""),
                betrag=_decimal(row.get("betrag")),
                kategorie=row.get("kategorie", ""),
                referenz_id=row.get("referenz_id", ""),
                error_types=row.get("error_types", ""),
                raw=dict(row),
            )


def _load_invoices(paths: Iterable[Path]) -> Iterable[_Invoice]:
    seen: set[str] = set()
    for path in paths:
        if not path.is_file():
            continue
        with path.open("r", encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                inv_id = row.get("id", "")
                if not inv_id or inv_id in seen:
                    continue
                seen.add(inv_id)
                yield _Invoice(
                    id=inv_id,
                    datum=row.get("datum", ""),
                    dl_id=row.get("dienstleister_id", ""),
                    brutto=_decimal(row.get("brutto")),
                    iban=row.get("iban", ""),
                    error_types=row.get("error_types", ""),
                    raw=dict(row),
                )


def _decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value).replace(",", "."))
    except (InvalidOperation, ValueError):
        return None


def render_markdown(report: ReconciliationReport) -> str:
    lines = [
        "---",
        "name: reconciliation",
        "description: Bank-to-invoice reconciliation surfaces.",
        "---",
        "",
        "## Summary",
        "",
        f"- bank transactions: {report.total_bank}",
        f"- invoices: {report.total_invoices}",
        f"- matched 1:1: {report.matched}",
        f"- anomalies: {len(report.anomalies)}",
        "",
        "## Anomaly Counts",
        "",
        "| Kind | Count |",
        "|---|---|",
    ]
    for kind, count in sorted(report.counts.items()):
        lines.append(f"| {kind} | {count} |")
    if not report.counts:
        lines.append("| _none_ | 0 |")

    lines.extend(["", "## Anomalies", ""])
    if not report.anomalies:
        lines.append("_no anomalies detected_")
    else:
        lines.append("| Kind | Detail | Refs |")
        lines.append("|---|---|---|")
        for a in report.anomalies:
            refs = ", ".join(f"{k}={v}" for k, v in a.refs.items())
            lines.append(f"| {a.kind} | {_escape(a.detail)} | {_escape(refs)} |")

    lines.extend(["", "# Human Notes", ""])
    return "\n".join(lines) + "\n"


def _escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def write_report(
    report: ReconciliationReport,
    *,
    output_path: Path,
    wiki_path: Path | None = None,
) -> None:
    body = render_markdown(report)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(output_path, body)
    if wiki_path is not None:
        wiki_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(wiki_path, body)


def _run_cli(args: argparse.Namespace) -> int:
    settings = get_settings()
    invoice_csvs = (
        list(args.invoice_csvs) if args.invoice_csvs else _default_invoice_csvs(settings.data_dir)
    )
    bank_csv = args.bank_csv or settings.data_dir / "bank" / "bank_index.csv"
    report = reconcile(bank_csv=bank_csv, invoice_csvs=invoice_csvs)
    output = args.output or settings.output_dir / "reconciliation.md"
    wiki = (
        settings.wiki_dir / args.property_id / "05_finances" / "reconciliation.md"
        if args.write_wiki
        else None
    )
    write_report(report, output_path=output, wiki_path=wiki)
    log.info(
        "reconcile_done",
        anomalies=len(report.anomalies),
        matched=report.matched,
        total_bank=report.total_bank,
        total_invoices=report.total_invoices,
        output=str(output),
    )
    return 0


def _default_invoice_csvs(data_dir: Path) -> list[Path]:
    incremental = data_dir / "incremental"
    if not incremental.is_dir():
        return []
    return sorted(incremental.glob("day-*/rechnungen_index.csv"))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Reconcile bank transactions against invoices, write report markdown."
    )
    parser.add_argument("--bank-csv", type=Path, default=None)
    parser.add_argument(
        "--invoice-csvs",
        type=Path,
        nargs="*",
        default=None,
        help="One or more rechnungen_index.csv paths.",
    )
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--property-id", type=str, default="LIE-001")
    parser.add_argument(
        "--write-wiki",
        action="store_true",
        help="Also write to wiki/<LIE-id>/05_finances/reconciliation.md",
    )
    args = parser.parse_args()
    raise SystemExit(_run_cli(args))


if __name__ == "__main__":
    main()


__all__ = ["Anomaly", "ReconciliationReport", "reconcile", "render_markdown", "write_report"]
