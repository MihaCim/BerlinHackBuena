from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from typing import Any

from .utils import money


def render_context(data: dict[str, Any], llm_advice: str = "") -> str:
    master = data["master"]
    prop = master["liegenschaft"]
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    sections = [
        render_frontmatter(prop, data["watermark"], now),
        f"# Property Context: {prop.get('name', 'Unknown Property')}",
        render_human_notes(),
        section("agent_brief", "Agent Brief", render_agent_brief(data, llm_advice)),
        section("property_snapshot", "Property Snapshot", render_property_snapshot(master)),
        section("buildings_units", "Buildings And Units", render_buildings_units(master)),
        section("owners", "Owners", render_owners(master)),
        section("tenants", "Tenants", render_tenants(master)),
        section("service_providers", "Service Providers", render_service_providers(master, data)),
        section("financial_state", "Financial State", render_financial_state(data)),
        section("open_topics", "Open Operational Topics", render_topics(data)),
        section("meetings_decisions", "Meetings And Decisions", render_meetings(data)),
        section("recent_communications", "Recent Communications", render_recent_communications(data)),
        section("invoices_payments", "Invoices And Payments", render_invoices(data)),
        section("risks_review", "Risks, Anomalies, And Review Items", render_anomalies(data)),
        section("timeline", "Timeline", render_timeline(data)),
        section("source_register", "Source Register", render_source_register(data)),
    ]
    return "\n\n".join(part.rstrip() for part in sections) + "\n"


def render_frontmatter(prop: dict[str, Any], watermark: str, generated_at: str) -> str:
    address = f"{prop.get('strasse', '')}, {prop.get('plz', '')} {prop.get('ort', '')}".strip()
    return "\n".join(
        [
            "---",
            f"property_id: {prop.get('id', '')}",
            f"property_name: {prop.get('name', '')}",
            f"address: {address}",
            f"generated_at: {generated_at}",
            "schema_version: 1",
            f"source_watermark: {watermark}",
            "---",
        ]
    )


def render_human_notes() -> str:
    return "\n".join(
        [
            "<!-- HUMAN_NOTES_START -->",
            "## Human Notes",
            "",
            "Human-maintained notes live here and must never be overwritten by the engine.",
            "<!-- HUMAN_NOTES_END -->",
        ]
    )


def section(anchor: str, title: str, body: str) -> str:
    return "\n".join([f"<!-- SECTION:{anchor} START -->", f"## {title}", "", body.rstrip(), f"<!-- SECTION:{anchor} END -->"])


def render_agent_brief(data: dict[str, Any], llm_advice: str = "") -> str:
    metrics = data["metrics"]
    lines = [
        "This is the canonical working context for the property. Use it before drafting emails, answering owner or tenant questions, reconciling invoices, or planning maintenance.",
        "",
        f"- Watermark: `{data['watermark']}`.",
        f"- Coverage: {metrics['bank_transactions']} bank transactions, {metrics['invoices']} invoices, {metrics['emails']} emails, {metrics['letters']} letters.",
        f"- Current topics: {metrics['topics']} open/high-signal topics.",
        f"- Review queue: {metrics['anomalies']} anomaly or attention items.",
        "- Use source IDs before taking irreversible financial or legal action.",
        "- Human notes and locked blocks are protected from automated patches.",
    ]
    if llm_advice:
        lines.extend(["", "Agentic AI note:", "", llm_advice])
    return "\n".join(lines)


def render_property_snapshot(master: dict[str, Any]) -> str:
    prop = master["liegenschaft"]
    return "\n".join(
        [
            f"- Property ID: `{prop.get('id')}`.",
            f"- Name: {prop.get('name')}.",
            f"- Address: {prop.get('strasse')}, {prop.get('plz')} {prop.get('ort')}.",
            f"- Manager: {prop.get('verwalter')} ({prop.get('verwalter_email')}).",
            f"- Buildings: {len(master.get('gebaeude', []))}.",
            f"- Units: {len(master.get('einheiten', []))}.",
            f"- Owners: {len(master.get('eigentuemer', []))}.",
            f"- Tenants: {len(master.get('mieter', []))}.",
            f"- Service providers: {len(master.get('dienstleister', []))}.",
            "- Source: [S:stammdaten:stammdaten.json].",
        ]
    )


def render_buildings_units(master: dict[str, Any]) -> str:
    units_by_building = defaultdict(list)
    for unit in master.get("einheiten", []):
        units_by_building[unit.get("haus_id")].append(unit)
    lines = ["| Building | Units | Elevator | Notes |", "|---|---:|---|---|"]
    for building in master.get("gebaeude", []):
        units = units_by_building.get(building.get("id"), [])
        elevator = "yes" if building.get("fahrstuhl") else "no"
        lines.append(f"| {building.get('id')} / Haus {building.get('hausnr')} | {len(units)} | {elevator} | Built {building.get('baujahr')} |")
    lines.extend(["", "Representative unit map:", "", "| Unit | Building | WE | Location | Area | Share |", "|---|---|---|---|---:|---:|"])
    for unit in master.get("einheiten", [])[:20]:
        lines.append(
            f"| {unit.get('id')} | {unit.get('haus_id')} | {unit.get('einheit_nr')} | {unit.get('lage')} | {unit.get('wohnflaeche_qm')} | {unit.get('miteigentumsanteil')} |"
        )
    lines.append("")
    lines.append("Full unit detail remains in `data/stammdaten/stammdaten.json`. Source: [S:stammdaten:einheiten].")
    return "\n".join(lines)


def render_owners(master: dict[str, Any]) -> str:
    lines = ["| Owner | Units | Self occupier | SEV | Advisory board | Contact |", "|---|---|---|---|---|---|"]
    for owner in master.get("eigentuemer", []):
        units = ", ".join(owner.get("einheit_ids") or [])
        lines.append(
            f"| {owner.get('id')} {owner.get('display_name')} | {units} | {yes_no(owner.get('selbstnutzer'))} | {yes_no(owner.get('sev_mandat'))} | {yes_no(owner.get('beirat'))} | {owner.get('email')} |"
        )
    lines.append("")
    lines.append("Source: [S:stammdaten:eigentuemer].")
    return "\n".join(lines)


def render_tenants(master: dict[str, Any]) -> str:
    lines = ["| Tenant | Unit | Owner | Rent + prepay | Lease | Contact |", "|---|---|---|---:|---|---|"]
    for tenant in master.get("mieter", []):
        rent = float(tenant.get("kaltmiete") or 0) + float(tenant.get("nk_vorauszahlung") or 0)
        end = tenant.get("mietende") or "active"
        lines.append(
            f"| {tenant.get('id')} {tenant.get('display_name')} | {tenant.get('einheit_id')} | {tenant.get('eigentuemer_id')} | {money(rent)} | {tenant.get('mietbeginn')} to {end} | {tenant.get('email')} |"
        )
    lines.append("")
    lines.append("Source: [S:stammdaten:mieter].")
    return "\n".join(lines)


def render_service_providers(master: dict[str, Any], data: dict[str, Any]) -> str:
    invoices_by_vendor = Counter(inv.get("vendor_id") for inv in data.get("invoices", []))
    lines = ["| Provider | Category | Contract | Invoice count | Contact |", "|---|---|---:|---:|---|"]
    for provider in master.get("dienstleister", []):
        contract = money(provider.get("vertrag_monatlich")) if provider.get("vertrag_monatlich") else f"{money(provider.get('stundensatz'))}/h"
        lines.append(
            f"| {provider.get('id')} {provider.get('firma')} | {provider.get('branche')} | {contract} | {invoices_by_vendor.get(provider.get('id'), 0)} | {provider.get('email')} |"
        )
    lines.append("")
    lines.append("Source: [S:stammdaten:dienstleister].")
    return "\n".join(lines)


def render_financial_state(data: dict[str, Any]) -> str:
    prop = data["master"]["liegenschaft"]
    rows = data.get("bank_rows", [])
    credits = sum(row["amount"] for row in rows if row.get("direction") == "CREDIT")
    debits = sum(row["amount"] for row in rows if row.get("direction") == "DEBIT")
    by_category = Counter(row.get("category") for row in rows)
    lines = [
        f"- Operating account: {prop.get('weg_bankkonto_bank')}, IBAN `{prop.get('weg_bankkonto_iban')}`. Source: [S:stammdaten:liegenschaft].",
        f"- Reserve account IBAN: `{prop.get('ruecklage_iban')}`. Source: [S:stammdaten:liegenschaft].",
        f"- Transactions loaded: {len(rows)}.",
        f"- Total credits: {money(credits)}.",
        f"- Total debits: {money(debits)}.",
        f"- Net movement in loaded rows: {money(credits - debits)}.",
        "",
        "| Category | Count |",
        "|---|---:|",
    ]
    for category, count in by_category.most_common():
        lines.append(f"| {category or 'unknown'} | {count} |")
    return "\n".join(lines)


def render_topics(data: dict[str, Any]) -> str:
    topics = sorted(data.get("topics", []), key=lambda t: t.get("latest", ""), reverse=True)[:20]
    if not topics:
        return "No open high-signal topics detected yet."
    lines = []
    for topic in topics:
        lines.extend(
            [
                f"### {topic['id']} - {topic['title']}",
                "",
                f"- Status: {topic['status']}.",
                f"- Priority: {topic['priority']}.",
                f"- Latest update: {topic['latest']}.",
                f"- Related entities: {', '.join(topic['entities']) if topic['entities'] else 'none detected'}.",
                f"- Summary: {topic['summary']}",
                f"- Sources: {', '.join(f'[{sid}]' for sid in topic['source_ids'])}.",
                "",
            ]
        )
    return "\n".join(lines).rstrip()


def render_meetings(data: dict[str, Any]) -> str:
    letters = data.get("letters", [])
    by_kind = Counter(letter.get("kind") for letter in letters)
    lines = ["| Letter type | Count |", "|---|---:|"]
    for kind, count in by_kind.most_common():
        lines.append(f"| {kind} | {count} |")
    recent = [letter for letter in letters if "etv" in letter.get("kind", "")][-8:]
    if recent:
        lines.extend(["", "Recent ETV-related letters:", ""])
        for letter in recent:
            lines.append(f"- {letter['date']}: {letter['kind']} `{letter['id']}`. Source: [{letter['source_id']}].")
    return "\n".join(lines)


def render_recent_communications(data: dict[str, Any]) -> str:
    emails = sorted(data.get("emails", []), key=lambda e: e.get("datetime", ""), reverse=True)
    selected = [email for email in emails if email.get("score", 0) >= 0.6][:25]
    if not selected:
        return "No high-signal communications detected."
    lines = ["| Date | Score | Direction | Category | Subject | Source |", "|---|---:|---|---|---|---|"]
    for email in selected:
        lines.append(
            f"| {email.get('datetime')} | {email.get('score')} | {email.get('direction')} | {email.get('category')} | {email.get('subject')} | [{email.get('source_id')}] |"
        )
    return "\n".join(lines)


def render_invoices(data: dict[str, Any]) -> str:
    invoices = sorted(data.get("invoices", []), key=lambda inv: inv.get("date", ""), reverse=True)
    matches = data.get("invoice_matches", {})
    recent = invoices[:30]
    matched = sum(1 for match in matches.values() if match.get("status") == "matched")
    lines = [
        f"- Invoices loaded: {len(invoices)}.",
        f"- Matched invoices: {matched}.",
        f"- Unmatched or not-yet-paid invoices: {len(invoices) - matched}.",
        "",
        "| Invoice | Date | Vendor | Gross | Payment status | Sources |",
        "|---|---|---|---:|---|---|",
    ]
    for invoice in recent:
        match = matches.get(invoice["id"], {})
        status = match.get("status", "unknown")
        tx = f" via {match.get('transaction_id')}" if match.get("transaction_id") else ""
        amount = money(invoice.get("gross")) if invoice.get("gross") else "unknown"
        lines.append(
            f"| {invoice['id']} | {invoice.get('date')} | {invoice.get('vendor_id')} {invoice.get('vendor_name', '')} | {amount} | {status}{tx} | [{invoice.get('source_id')}] |"
        )
    return "\n".join(lines)


def render_anomalies(data: dict[str, Any]) -> str:
    anomalies = data.get("anomalies", [])
    if not anomalies:
        return "No anomalies detected."
    lines = ["| Severity | Kind | Summary | Sources |", "|---|---|---|---|"]
    for item in anomalies[:80]:
        sources = ", ".join(f"[{source}]" for source in item.get("source_ids", []))
        lines.append(f"| {item.get('severity')} | {item.get('kind')} | {item.get('summary')} | {sources} |")
    return "\n".join(lines)


def render_timeline(data: dict[str, Any]) -> str:
    events = []
    for email in data.get("emails", []):
        if email.get("score", 0) >= 0.7:
            events.append((email.get("datetime", ""), f"High-signal email `{email['id']}`: {email.get('subject')}. Source: [{email['source_id']}]."))
    for invoice in data.get("invoices", []):
        if invoice.get("gross"):
            events.append((invoice.get("date", ""), f"Invoice `{invoice['id']}` received for {money(invoice.get('gross'))}. Source: [{invoice['source_id']}]."))
    for bank in data.get("bank_rows", []):
        if bank.get("date", "").startswith("2026"):
            events.append((bank.get("date", ""), f"Bank transaction `{bank['id']}` {bank.get('direction')} {money(bank.get('amount'))}. Source: [{bank['source_id']}]."))
    events = sorted(events, key=lambda item: item[0], reverse=True)[:80]
    if not events:
        return "No timeline events selected."
    return "\n".join(f"- {date}: {text}" for date, text in events)


def render_source_register(data: dict[str, Any]) -> str:
    metrics = data["metrics"]
    return "\n".join(
        [
            "| Source family | Count |",
            "|---|---:|",
            f"| Master data entities | {len(data['master'].get('einheiten', [])) + len(data['master'].get('eigentuemer', [])) + len(data['master'].get('mieter', [])) + len(data['master'].get('dienstleister', []))} |",
            f"| Bank transactions | {metrics['bank_transactions']} |",
            f"| Emails | {metrics['emails']} |",
            f"| Invoices | {metrics['invoices']} |",
            f"| Letters | {metrics['letters']} |",
            "",
            "Source IDs are machine-resolvable through `context.meta.json` and `provenance.sqlite`.",
        ]
    )


def yes_no(value: Any) -> str:
    return "yes" if bool(value) else "no"

