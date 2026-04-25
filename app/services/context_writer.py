from __future__ import annotations

import asyncio
import hashlib
import json
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

JsonRecord = dict[str, object]

HUMAN_NOTES_HEADING = "# Human Notes"
STAMMDATEN_NOTE = "[^stammdaten]"
SOURCE_MANIFESTS = (
    ("master_data", "stammdaten", "stammdaten.md"),
    ("bank", "bank", "bank_transactions.md"),
    ("invoice", "rechnungen", "rechnungen.md"),
    ("letter", "briefe", "briefe.md"),
    ("email", "emails", "emails.md"),
)


@dataclass(frozen=True)
class ContextDataset:
    liegenschaft: JsonRecord
    buildings: list[JsonRecord]
    units: list[JsonRecord]
    owners: list[JsonRecord]
    tenants: list[JsonRecord]
    providers: list[JsonRecord]


@dataclass(frozen=True)
class Relationships:
    buildings_by_id: dict[str, JsonRecord]
    units_by_id: dict[str, JsonRecord]
    owners_by_id: dict[str, JsonRecord]
    tenants_by_id: dict[str, JsonRecord]
    units_by_building_id: dict[str, list[JsonRecord]]
    owners_by_unit_id: dict[str, list[JsonRecord]]
    tenant_by_unit_id: dict[str, JsonRecord]
    tenants_by_owner_id: dict[str, list[JsonRecord]]


@dataclass(frozen=True)
class Provenance:
    normalized_path: str
    source_path: str
    content_hash: str
    normalized_at: str


@dataclass(frozen=True)
class SourceFile:
    normalized_path: Path
    relative_path: str
    source_id: str
    source_type: str
    source_path: str
    content_hash: str
    normalized_at: str
    size_bytes: str


@dataclass(frozen=True)
class MarkdownFile:
    path: Path
    content: str


class ContextWriterService:
    """Writes deterministic context pages from normalized and raw base sources."""

    def __init__(self, data_dir: Path, normalize_dir: Path, output_dir: Path) -> None:
        self.data_dir = data_dir
        self.normalize_dir = normalize_dir
        self.output_dir = output_dir
        self.repo_root = data_dir.parent

    async def build_base_context(self, overwrite: bool = True) -> dict[str, object]:
        return await asyncio.to_thread(self._build_base_context_sync, overwrite)

    async def status(self) -> dict[str, object]:
        return await asyncio.to_thread(self._status_sync)

    def _build_base_context_sync(self, overwrite: bool) -> dict[str, object]:
        dataset = self._load_dataset()
        relationships = build_relationships(dataset)
        source_files = self._source_files()
        provenance = self._stammdaten_provenance()
        liegenschaft_id = text_value(dataset.liegenschaft, "id")
        output_root = self.output_dir / liegenschaft_id
        files = self._markdown_files(dataset, relationships, source_files, provenance, output_root)

        written: list[str] = []
        skipped: list[str] = []
        for file in files:
            if self._write_markdown(file.path, file.content, overwrite):
                written.append(self._display_path(file.path))
            else:
                skipped.append(self._display_path(file.path))

        state_path = output_root / "_state.json"
        if self._write_state(state_path, dataset, source_files, provenance, overwrite):
            written.append(self._display_path(state_path))
        else:
            skipped.append(self._display_path(state_path))

        return {
            "status": "completed",
            "liegenschaft_id": liegenschaft_id,
            "counts": counts_for(dataset, source_files),
            "files_written": len(written),
            "files_skipped": len(skipped),
            "output_root": self._display_path(output_root),
            "written": written,
            "skipped": skipped,
        }

    def _status_sync(self) -> dict[str, object]:
        markdown_files = tuple(self.output_dir.rglob("*.md")) if self.output_dir.exists() else ()
        state_files = (
            tuple(self.output_dir.rglob("_state.json")) if self.output_dir.exists() else ()
        )
        return {
            "output_dir": self._display_path(self.output_dir),
            "markdown_files": len(markdown_files),
            "state_files": len(state_files),
        }

    def _load_dataset(self) -> ContextDataset:
        path = self.data_dir / "stammdaten" / "stammdaten.json"
        if not path.exists():
            raise FileNotFoundError(f"Master data not found: {path}")

        with path.open("r", encoding="utf-8") as f:
            data = cast(JsonRecord, json.load(f))

        return ContextDataset(
            liegenschaft=record_value(data, "liegenschaft"),
            buildings=record_list(data, "gebaeude"),
            units=record_list(data, "einheiten"),
            owners=record_list(data, "eigentuemer"),
            tenants=record_list(data, "mieter"),
            providers=record_list(data, "dienstleister"),
        )

    def _source_files(self) -> list[SourceFile]:
        base_dir = self.normalize_dir / "base"
        if not base_dir.exists():
            return []

        files: list[SourceFile] = []
        for path in sorted(base_dir.rglob("*.md")):
            metadata = normalized_metadata(path)
            files.append(
                SourceFile(
                    normalized_path=path,
                    relative_path=self._display_path(path),
                    source_id=metadata.get("source_id", path.stem),
                    source_type=metadata.get("source_type", "unknown"),
                    source_path=metadata.get("source_path", ""),
                    content_hash=metadata.get("content_hash", ""),
                    normalized_at=metadata.get("normalized_at", ""),
                    size_bytes=metadata.get("size_bytes", ""),
                )
            )
        return files

    def _stammdaten_provenance(self) -> Provenance:
        normalized_path = self.normalize_dir / "base" / "stammdaten" / "stammdaten.md"
        raw_path = self.data_dir / "stammdaten" / "stammdaten.json"
        metadata = normalized_metadata(normalized_path) if normalized_path.exists() else {}
        return Provenance(
            normalized_path=self._display_path(normalized_path),
            source_path=metadata.get("source_path", self._display_path(raw_path)),
            content_hash=metadata.get(
                "content_hash", file_hash(raw_path) if raw_path.exists() else ""
            ),
            normalized_at=metadata.get("normalized_at", "not normalized"),
        )

    def _markdown_files(
        self,
        dataset: ContextDataset,
        relationships: Relationships,
        source_files: list[SourceFile],
        provenance: Provenance,
        output_root: Path,
    ) -> list[MarkdownFile]:
        files = [
            MarkdownFile(
                self.output_dir / "index.md",
                render_catalog(dataset, relationships, source_files, provenance),
            ),
            MarkdownFile(
                output_root / "building.md",
                render_property(dataset, relationships, source_files, provenance),
            ),
            MarkdownFile(
                output_root / "02_buildings" / "index.md",
                render_buildings_index(dataset, relationships, provenance),
            ),
            MarkdownFile(
                output_root / "03_people" / "index.md",
                render_people_index(dataset, provenance),
            ),
            MarkdownFile(
                output_root / "03_people" / "eigentuemer" / "index.md",
                render_owners_index(dataset, relationships, provenance),
            ),
            MarkdownFile(
                output_root / "03_people" / "mieter" / "index.md",
                render_tenants_index(dataset, relationships, provenance),
            ),
            MarkdownFile(
                output_root / "04_dienstleister" / "index.md",
                render_providers_index(dataset, provenance),
            ),
            MarkdownFile(
                output_root / "05_finances" / "index.md",
                render_finances(dataset, relationships, provenance),
            ),
            MarkdownFile(
                output_root / "06_sources" / "index.md",
                render_sources_index(dataset, source_files, provenance),
            ),
            MarkdownFile(output_root / "log.md", render_log(dataset, provenance)),
            MarkdownFile(
                output_root / "_pending_review.md",
                render_pending_review(dataset, relationships, provenance),
            ),
        ]
        files.extend(self._building_files(dataset, relationships, provenance, output_root))
        files.extend(self._person_files(dataset, relationships, provenance, output_root))
        files.extend(self._provider_files(dataset, provenance, output_root))
        files.extend(self._source_files_markdown(dataset, source_files, provenance, output_root))
        return files

    def _building_files(
        self,
        dataset: ContextDataset,
        relationships: Relationships,
        provenance: Provenance,
        output_root: Path,
    ) -> list[MarkdownFile]:
        files: list[MarkdownFile] = []
        for building in dataset.buildings:
            building_id = text_value(building, "id")
            building_dir = output_root / "02_buildings" / building_id
            files.append(
                MarkdownFile(
                    building_dir / "index.md",
                    render_building(dataset, building, relationships, provenance),
                )
            )
            for unit in relationships.units_by_building_id.get(building_id, []):
                files.append(
                    MarkdownFile(
                        building_dir / "units" / f"{text_value(unit, 'id')}.md",
                        render_unit(dataset, unit, relationships, provenance),
                    )
                )
        return files

    def _person_files(
        self,
        dataset: ContextDataset,
        relationships: Relationships,
        provenance: Provenance,
        output_root: Path,
    ) -> list[MarkdownFile]:
        files: list[MarkdownFile] = []
        for owner in dataset.owners:
            files.append(
                MarkdownFile(
                    output_root / "03_people" / "eigentuemer" / f"{text_value(owner, 'id')}.md",
                    render_owner(owner, relationships, provenance),
                )
            )
        for tenant in dataset.tenants:
            files.append(
                MarkdownFile(
                    output_root / "03_people" / "mieter" / f"{text_value(tenant, 'id')}.md",
                    render_tenant(tenant, relationships, provenance),
                )
            )
        return files

    def _provider_files(
        self,
        dataset: ContextDataset,
        provenance: Provenance,
        output_root: Path,
    ) -> list[MarkdownFile]:
        return [
            MarkdownFile(
                output_root / "04_dienstleister" / f"{text_value(provider, 'id')}.md",
                render_provider(provider, provenance),
            )
            for provider in dataset.providers
        ]

    def _source_files_markdown(
        self,
        dataset: ContextDataset,
        source_files: list[SourceFile],
        provenance: Provenance,
        output_root: Path,
    ) -> list[MarkdownFile]:
        return [
            MarkdownFile(
                output_root / "06_sources" / "bank_transactions.md",
                render_bank_transactions(source_files, self.normalize_dir, provenance),
            ),
            MarkdownFile(
                output_root / "06_sources" / "rechnungen.md",
                render_source_manifest("invoice", "rechnungen", source_files, provenance),
            ),
            MarkdownFile(
                output_root / "06_sources" / "briefe.md",
                render_source_manifest("letter", "briefe", source_files, provenance),
            ),
            MarkdownFile(
                output_root / "06_sources" / "emails.md",
                render_source_manifest("email", "emails", source_files, provenance),
            ),
            MarkdownFile(
                output_root / "06_sources" / "stammdaten.md",
                render_source_manifest("master_data", "stammdaten", source_files, provenance),
            ),
            MarkdownFile(
                output_root / "06_sources" / "source_counts.md",
                render_source_counts(dataset, source_files, provenance),
            ),
        ]

    def _write_markdown(self, path: Path, content: str, overwrite: bool) -> bool:
        if path.exists() and not overwrite:
            return False

        human_notes = extract_human_notes(path.read_text(encoding="utf-8")) if path.exists() else ""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(with_human_notes(content, human_notes), encoding="utf-8")
        return True

    def _write_state(
        self,
        path: Path,
        dataset: ContextDataset,
        source_files: list[SourceFile],
        provenance: Provenance,
        overwrite: bool,
    ) -> bool:
        if path.exists() and not overwrite:
            return False

        state = {
            "last_patched": datetime.now(UTC).isoformat(),
            "source_id": "stammdaten",
            "source_path": provenance.source_path,
            "normalized_path": provenance.normalized_path,
            "hash": provenance.content_hash,
            "counts": counts_for(dataset, source_files),
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return True

    def _display_path(self, path: Path) -> str:
        for root in (self.repo_root, self.output_dir.parent, self.normalize_dir.parent):
            try:
                return str(path.relative_to(root))
            except ValueError:
                continue
        return str(path)


def render_catalog(
    dataset: ContextDataset,
    relationships: Relationships,
    source_files: list[SourceFile],
    provenance: Provenance,
) -> str:
    lines = front_matter(
        "property-catalog",
        "Global catalog of managed properties and context entry points.",
    )
    lines.extend(["# Property Catalog", ""])
    lines.extend(section("catalog", catalog_rows(dataset, relationships, source_files)))
    lines.extend(provenance_section(provenance))
    return "\n".join(lines)


def render_property(
    dataset: ContextDataset,
    relationships: Relationships,
    source_files: list[SourceFile],
    provenance: Provenance,
) -> str:
    liegenschaft = dataset.liegenschaft
    liegenschaft_id = text_value(liegenschaft, "id")
    description = (
        f"Living context for {text_value(liegenschaft, 'name')} ({liegenschaft_id}); "
        f"{len(dataset.buildings)} buildings, {len(dataset.units)} units, "
        f"{len(dataset.owners)} owners, {len(dataset.tenants)} tenants, "
        f"{len(dataset.providers)} service providers."
    )
    lines = front_matter(slug(liegenschaft_id, text_value(liegenschaft, "name")), description)
    lines.extend([f"# {liegenschaft_id} {text_value(liegenschaft, 'name')}", ""])
    lines.extend(section("summary", property_summary(dataset)))
    lines.extend(section("buildings", property_building_table(dataset, relationships)))
    lines.extend(section("people", property_people_summary(dataset)))
    lines.extend(section("finance", property_finance_summary(dataset)))
    lines.extend(section("sources", property_source_summary(source_files)))
    lines.extend(section("routing", property_routing(dataset)))
    lines.extend(
        section("open_issues", ["## Open Issues", "", f"- None recorded {STAMMDATEN_NOTE}", ""])
    )
    lines.extend(section("recent_events", recent_event_lines("Property context generated")))
    lines.extend(provenance_section(provenance))
    return "\n".join(lines)


def render_buildings_index(
    dataset: ContextDataset,
    relationships: Relationships,
    provenance: Provenance,
) -> str:
    lines = front_matter("buildings-index", "Index of buildings for the property.")
    lines.extend(["# Buildings", ""])
    table = [
        "| ID | House No. | Floors | Elevator | Units | Area qm | Source |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for building in dataset.buildings:
        building_id = text_value(building, "id")
        units = relationships.units_by_building_id.get(building_id, [])
        table.append(
            "| "
            + " | ".join(
                [
                    link(building_id, f"{building_id}/index.md"),
                    md(text_value(building, "hausnr")),
                    md(text_value(building, "etagen")),
                    md(yes_no(bool_value(building, "fahrstuhl"))),
                    str(len(units)),
                    format_number(sum(number_value(unit, "wohnflaeche_qm") for unit in units)),
                    STAMMDATEN_NOTE,
                ]
            )
            + " |"
        )
    lines.extend(section("buildings", ["## Building Register", "", *table, ""]))
    lines.extend(provenance_section(provenance))
    return "\n".join(lines)


def render_building(
    dataset: ContextDataset,
    building: JsonRecord,
    relationships: Relationships,
    provenance: Provenance,
) -> str:
    building_id = text_value(building, "id")
    units = relationships.units_by_building_id.get(building_id, [])
    lines = front_matter(
        slug(building_id, "haus", text_value(building, "hausnr")),
        f"Building context for {building_id} with {len(units)} units.",
    )
    lines.extend([f"# {building_id}", ""])
    lines.extend(section("summary", building_summary(building, units)))
    lines.extend(section("units", building_unit_table(units, relationships)))
    lines.extend(
        section("open_issues", ["## Open Issues", "", f"- None recorded {STAMMDATEN_NOTE}", ""])
    )
    lines.extend(section("recent_events", recent_event_lines("Building context generated")))
    lines.extend(provenance_section(provenance))
    return "\n".join(lines)


def render_unit(
    dataset: ContextDataset,
    unit: JsonRecord,
    relationships: Relationships,
    provenance: Provenance,
) -> str:
    unit_id = text_value(unit, "id")
    building_id = text_value(unit, "haus_id")
    owners = relationships.owners_by_unit_id.get(unit_id, [])
    tenant = relationships.tenant_by_unit_id.get(unit_id)
    lines = front_matter(
        slug(unit_id, text_value(unit, "einheit_nr")),
        f"Unit {unit_id} in {building_id} with ownership and tenancy links.",
    )
    lines.extend([f"# {unit_id} {text_value(unit, 'einheit_nr')}", ""])
    lines.extend(section("facts", unit_facts(unit, building_id, owners, tenant)))
    lines.extend(section("ownership", unit_ownership(owners)))
    lines.extend(section("tenancy", unit_tenancy(tenant)))
    lines.extend(section("history", recent_event_lines("Unit context generated")))
    lines.extend(provenance_section(provenance))
    return "\n".join(lines)


def render_people_index(dataset: ContextDataset, provenance: Provenance) -> str:
    lines = front_matter("people-index", "Index of owners and tenants.")
    lines.extend(["# People", ""])
    body = [
        "## Registers",
        "",
        f"- Owners: {len(dataset.owners)} in `eigentuemer/index.md` {STAMMDATEN_NOTE}",
        f"- Tenants: {len(dataset.tenants)} in `mieter/index.md` {STAMMDATEN_NOTE}",
        "",
    ]
    lines.extend(section("registers", body))
    lines.extend(provenance_section(provenance))
    return "\n".join(lines)


def render_owners_index(
    dataset: ContextDataset,
    relationships: Relationships,
    provenance: Provenance,
) -> str:
    lines = front_matter("owners-index", "Owner register with unit assignments and contact data.")
    lines.extend(["# Owners", ""])
    lines.extend(section("owners", owner_index_table(dataset.owners, relationships)))
    lines.extend(provenance_section(provenance))
    return "\n".join(lines)


def render_owner(
    owner: JsonRecord,
    relationships: Relationships,
    provenance: Provenance,
) -> str:
    owner_id = text_value(owner, "id")
    units = [relationships.units_by_id[unit_id] for unit_id in id_list(owner, "einheit_ids")]
    tenants = relationships.tenants_by_owner_id.get(owner_id, [])
    lines = front_matter(slug(owner_id, display_name(owner)), f"Owner context for {owner_id}.")
    lines.extend([f"# {owner_id} {display_name(owner)}", ""])
    lines.extend(section("contact", owner_contact(owner)))
    lines.extend(section("ownership", owner_units(units)))
    lines.extend(section("tenant_links", owner_tenant_links(tenants)))
    lines.extend(section("banking", owner_banking(owner)))
    lines.extend(provenance_section(provenance))
    return "\n".join(lines)


def render_tenants_index(
    dataset: ContextDataset,
    relationships: Relationships,
    provenance: Provenance,
) -> str:
    lines = front_matter("tenants-index", "Tenant register with unit, owner, and rent data.")
    lines.extend(["# Tenants", ""])
    lines.extend(section("tenants", tenant_index_table(dataset.tenants, relationships)))
    lines.extend(provenance_section(provenance))
    return "\n".join(lines)


def render_tenant(
    tenant: JsonRecord,
    relationships: Relationships,
    provenance: Provenance,
) -> str:
    tenant_id = text_value(tenant, "id")
    lines = front_matter(slug(tenant_id, display_name(tenant)), f"Tenant context for {tenant_id}.")
    lines.extend([f"# {tenant_id} {display_name(tenant)}", ""])
    lines.extend(section("contact", tenant_contact(tenant)))
    lines.extend(section("tenancy", tenant_tenancy(tenant, relationships)))
    lines.extend(section("banking", tenant_banking(tenant)))
    lines.extend(provenance_section(provenance))
    return "\n".join(lines)


def render_providers_index(dataset: ContextDataset, provenance: Provenance) -> str:
    lines = front_matter(
        "providers-index", "Service-provider register with contact and contract data."
    )
    lines.extend(["# Service Providers", ""])
    lines.extend(section("providers", provider_index_table(dataset.providers)))
    lines.extend(provenance_section(provenance))
    return "\n".join(lines)


def render_provider(provider: JsonRecord, provenance: Provenance) -> str:
    provider_id = text_value(provider, "id")
    lines = front_matter(
        slug(provider_id, text_value(provider, "firma")),
        f"Service-provider context for {provider_id}.",
    )
    lines.extend([f"# {provider_id} {text_value(provider, 'firma')}", ""])
    lines.extend(section("contact", provider_contact(provider)))
    lines.extend(section("billing", provider_billing(provider)))
    lines.extend(section("contract", provider_contract(provider)))
    lines.extend(provenance_section(provenance))
    return "\n".join(lines)


def render_finances(
    dataset: ContextDataset,
    relationships: Relationships,
    provenance: Provenance,
) -> str:
    lines = front_matter("finance-overview", "Finance overview from master data.")
    lines.extend(["# Finance Overview", ""])
    lines.extend(section("accounts", finance_accounts(dataset.liegenschaft)))
    lines.extend(section("rent_roll", finance_rent_roll(dataset.tenants, relationships)))
    lines.extend(section("owner_payment_flags", finance_owner_flags(dataset.owners)))
    lines.extend(section("provider_contracts", finance_provider_contracts(dataset.providers)))
    lines.extend(provenance_section(provenance))
    return "\n".join(lines)


def render_log(dataset: ContextDataset, provenance: Provenance) -> str:
    today = datetime.now(UTC).date().isoformat()
    lines = front_matter("event-log", "Deterministic event log for generated context.")
    lines.extend([f"# {text_value(dataset.liegenschaft, 'id')} Event Log", ""])
    body = [
        "## Deterministic Builds",
        "",
        f"- {today}: Base context generated from master data {STAMMDATEN_NOTE}",
        f"- {today}: Source manifests generated from normalized base corpus {STAMMDATEN_NOTE}",
        "",
    ]
    lines.extend(section("builds", body))
    lines.extend(provenance_section(provenance))
    return "\n".join(lines)


def render_pending_review(
    dataset: ContextDataset,
    relationships: Relationships,
    provenance: Provenance,
) -> str:
    issues = relationship_issues(dataset, relationships)
    lines = front_matter("pending-review", "Deterministic validation queue for unresolved links.")
    lines.extend(["# Pending Review", ""])
    if issues:
        body = [
            "## Relationship Issues",
            "",
            *[f"- {md(issue)} {STAMMDATEN_NOTE}" for issue in issues],
            "",
        ]
    else:
        body = [
            "## Relationship Issues",
            "",
            f"- No unresolved master-data links {STAMMDATEN_NOTE}",
            "",
        ]
    lines.extend(section("relationship_issues", body))
    lines.extend(provenance_section(provenance))
    return "\n".join(lines)


def render_sources_index(
    dataset: ContextDataset,
    source_files: list[SourceFile],
    provenance: Provenance,
) -> str:
    counts = source_counts(source_files)
    lines = front_matter(
        "source-index", "Index of normalized source manifests used by the context."
    )
    lines.extend(["# Source Index", ""])
    body = [
        "## Source Manifests",
        "",
        "| Source Type | Files | Manifest | Source |",
        "| --- | --- | --- | --- |",
    ]
    for source_type, label, manifest in SOURCE_MANIFESTS:
        body.append(
            f"| {md(label)} | {counts.get(source_type, 0)} | "
            f"{link(manifest, manifest)} | {STAMMDATEN_NOTE} |"
        )
    body.extend(
        [
            "",
            f"- Master-data entities: {len(dataset.units)} units, {len(dataset.owners)} owners, "
            f"{len(dataset.tenants)} tenants, {len(dataset.providers)} providers {STAMMDATEN_NOTE}",
            "",
        ]
    )
    lines.extend(section("manifests", body))
    lines.extend(provenance_section(provenance))
    return "\n".join(lines)


def render_bank_transactions(
    source_files: list[SourceFile],
    normalize_dir: Path,
    provenance: Provenance,
) -> str:
    lines = front_matter("bank-transactions", "Bank source manifest and transaction index.")
    lines.extend(["# Bank Transactions", ""])
    lines.extend(section("bank_files", source_table("bank", source_files)))
    transaction_table = normalized_bank_index_table(normalize_dir)
    if transaction_table:
        lines.extend(section("transactions", transaction_table))
    else:
        lines.extend(
            section(
                "transactions",
                ["## Transactions", "", "- No normalized bank index found [^bank_index]", ""],
            )
        )
    lines.extend(bank_provenance_section(provenance))
    return "\n".join(lines)


def render_source_manifest(
    source_type: str,
    label: str,
    source_files: list[SourceFile],
    provenance: Provenance,
) -> str:
    lines = front_matter(
        f"{label}-manifest",
        f"Normalized source manifest for {label}.",
    )
    lines.extend([f"# {label.title()} Sources", ""])
    lines.extend(section("sources", source_table(source_type, source_files)))
    lines.extend(provenance_section(provenance))
    return "\n".join(lines)


def render_source_counts(
    dataset: ContextDataset,
    source_files: list[SourceFile],
    provenance: Provenance,
) -> str:
    lines = front_matter("source-counts", "Source and entity counts for deterministic validation.")
    lines.extend(["# Source Counts", ""])
    body = [
        "## Counts",
        "",
        "| Item | Count | Source |",
        "| --- | --- | --- |",
    ]
    for key, value in counts_for(dataset, source_files).items():
        body.append(f"| {md(key)} | {value} | {STAMMDATEN_NOTE} |")
    body.append("")
    lines.extend(section("counts", body))
    lines.extend(provenance_section(provenance))
    return "\n".join(lines)


def build_relationships(dataset: ContextDataset) -> Relationships:
    buildings_by_id = {text_value(building, "id"): building for building in dataset.buildings}
    units_by_id = {text_value(unit, "id"): unit for unit in dataset.units}
    owners_by_id = {text_value(owner, "id"): owner for owner in dataset.owners}
    tenants_by_id = {text_value(tenant, "id"): tenant for tenant in dataset.tenants}
    units_by_building_id: dict[str, list[JsonRecord]] = defaultdict(list)
    owners_by_unit_id: dict[str, list[JsonRecord]] = defaultdict(list)
    tenants_by_owner_id: dict[str, list[JsonRecord]] = defaultdict(list)
    tenant_by_unit_id: dict[str, JsonRecord] = {}

    for unit in dataset.units:
        units_by_building_id[text_value(unit, "haus_id")].append(unit)
    for owner in dataset.owners:
        for unit_id in id_list(owner, "einheit_ids"):
            owners_by_unit_id[unit_id].append(owner)
    for tenant in dataset.tenants:
        tenant_by_unit_id[text_value(tenant, "einheit_id")] = tenant
        tenants_by_owner_id[text_value(tenant, "eigentuemer_id")].append(tenant)

    return Relationships(
        buildings_by_id=buildings_by_id,
        units_by_id=units_by_id,
        owners_by_id=owners_by_id,
        tenants_by_id=tenants_by_id,
        units_by_building_id=dict(units_by_building_id),
        owners_by_unit_id=dict(owners_by_unit_id),
        tenant_by_unit_id=tenant_by_unit_id,
        tenants_by_owner_id=dict(tenants_by_owner_id),
    )


def catalog_rows(
    dataset: ContextDataset,
    relationships: Relationships,
    source_files: list[SourceFile],
) -> list[str]:
    liegenschaft = dataset.liegenschaft
    liegenschaft_id = text_value(liegenschaft, "id")
    return [
        "## Properties",
        "",
        "| ID | Name | Address | Buildings | Units | Sources | Entry | Source |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
        "| "
        + " | ".join(
            [
                md(liegenschaft_id),
                md(text_value(liegenschaft, "name")),
                md(address(liegenschaft)),
                str(len(relationships.buildings_by_id)),
                str(len(dataset.units)),
                str(len(source_files)),
                link("building.md", f"{liegenschaft_id}/building.md"),
                STAMMDATEN_NOTE,
            ]
        )
        + " |",
        "",
    ]


def property_summary(dataset: ContextDataset) -> list[str]:
    liegenschaft = dataset.liegenschaft
    return [
        "## Summary",
        "",
        f"- ID: {text_value(liegenschaft, 'id')} {STAMMDATEN_NOTE}",
        f"- Name: {text_value(liegenschaft, 'name')} {STAMMDATEN_NOTE}",
        f"- Address: {address(liegenschaft)} {STAMMDATEN_NOTE}",
        f"- Construction year: {text_value(liegenschaft, 'baujahr')} {STAMMDATEN_NOTE}",
        f"- Renovation year: {text_value(liegenschaft, 'sanierung')} {STAMMDATEN_NOTE}",
        f"- Verwalter: {text_value(liegenschaft, 'verwalter')} {STAMMDATEN_NOTE}",
        f"- Verwalter contact: {text_value(liegenschaft, 'verwalter_email')}, "
        f"{text_value(liegenschaft, 'verwalter_telefon')} {STAMMDATEN_NOTE}",
        "",
    ]


def property_building_table(dataset: ContextDataset, relationships: Relationships) -> list[str]:
    rows = [
        "## Buildings",
        "",
        "| ID | House No. | Floors | Elevator | Units | Area qm | MEA | Source |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for building in dataset.buildings:
        building_id = text_value(building, "id")
        units = relationships.units_by_building_id.get(building_id, [])
        rows.append(
            "| "
            + " | ".join(
                [
                    link(building_id, f"02_buildings/{building_id}/index.md"),
                    md(text_value(building, "hausnr")),
                    md(text_value(building, "etagen")),
                    md(yes_no(bool_value(building, "fahrstuhl"))),
                    str(len(units)),
                    format_number(sum(number_value(unit, "wohnflaeche_qm") for unit in units)),
                    format_number(sum(number_value(unit, "miteigentumsanteil") for unit in units)),
                    STAMMDATEN_NOTE,
                ]
            )
            + " |"
        )
    rows.append("")
    return rows


def property_people_summary(dataset: ContextDataset) -> list[str]:
    beirat_count = sum(1 for owner in dataset.owners if bool_value(owner, "beirat"))
    sev_count = sum(1 for owner in dataset.owners if bool_value(owner, "sev_mandat"))
    self_user_count = sum(1 for owner in dataset.owners if bool_value(owner, "selbstnutzer"))
    return [
        "## People",
        "",
        f"- Owners: {len(dataset.owners)} {STAMMDATEN_NOTE}",
        f"- Tenants: {len(dataset.tenants)} {STAMMDATEN_NOTE}",
        f"- Self-using owners: {self_user_count} {STAMMDATEN_NOTE}",
        f"- Owners with SEV mandate: {sev_count} {STAMMDATEN_NOTE}",
        f"- Advisory-board owners: {beirat_count} {STAMMDATEN_NOTE}",
        f"- Owner register: `03_people/eigentuemer/index.md` {STAMMDATEN_NOTE}",
        f"- Tenant register: `03_people/mieter/index.md` {STAMMDATEN_NOTE}",
        "",
    ]


def property_finance_summary(dataset: ContextDataset) -> list[str]:
    liegenschaft = dataset.liegenschaft
    monthly_rent = sum(number_value(tenant, "kaltmiete") for tenant in dataset.tenants)
    monthly_nk = sum(number_value(tenant, "nk_vorauszahlung") for tenant in dataset.tenants)
    provider_contracts = sum(
        number_value(provider, "vertrag_monatlich") for provider in dataset.providers
    )
    return [
        "## Finance",
        "",
        f"- WEG account: {text_value(liegenschaft, 'weg_bankkonto_bank')}, "
        f"IBAN {text_value(liegenschaft, 'weg_bankkonto_iban')} {STAMMDATEN_NOTE}",
        f"- Reserve account: IBAN {text_value(liegenschaft, 'ruecklage_iban')} {STAMMDATEN_NOTE}",
        f"- Tenant cold-rent roll: {format_money(monthly_rent)} monthly {STAMMDATEN_NOTE}",
        f"- Tenant NK prepayments: {format_money(monthly_nk)} monthly {STAMMDATEN_NOTE}",
        f"- Provider fixed monthly contracts: {format_money(provider_contracts)} {STAMMDATEN_NOTE}",
        f"- Finance details: `05_finances/index.md` {STAMMDATEN_NOTE}",
        "",
    ]


def property_source_summary(source_files: list[SourceFile]) -> list[str]:
    counts = source_counts(source_files)
    rows = [
        "## Normalized Source Coverage",
        "",
        "| Type | Files | Manifest | Source |",
        "| --- | --- | --- | --- |",
    ]
    for source_type, label, manifest_name in SOURCE_MANIFESTS:
        manifest = f"06_sources/{manifest_name}"
        rows.append(
            f"| {md(label)} | {counts.get(source_type, 0)} | "
            f"{link(manifest, manifest)} | {STAMMDATEN_NOTE} |"
        )
    rows.append("")
    return rows


def property_routing(dataset: ContextDataset) -> list[str]:
    liegenschaft_id = text_value(dataset.liegenschaft, "id")
    return [
        "## Routing",
        "",
        f"- Buildings and units: `02_buildings/index.md` {STAMMDATEN_NOTE}",
        f"- Owners and tenants: `03_people/index.md` {STAMMDATEN_NOTE}",
        f"- Service providers: `04_dienstleister/index.md` {STAMMDATEN_NOTE}",
        f"- Finance overview: `05_finances/index.md` {STAMMDATEN_NOTE}",
        f"- Source manifests: `06_sources/index.md` {STAMMDATEN_NOTE}",
        f"- Scope: generated files are scoped to {liegenschaft_id} {STAMMDATEN_NOTE}",
        "",
    ]


def building_summary(building: JsonRecord, units: list[JsonRecord]) -> list[str]:
    total_area = sum(number_value(unit, "wohnflaeche_qm") for unit in units)
    total_mea = sum(number_value(unit, "miteigentumsanteil") for unit in units)
    return [
        "## Summary",
        "",
        f"- Building ID: {text_value(building, 'id')} {STAMMDATEN_NOTE}",
        f"- House number: {text_value(building, 'hausnr')} {STAMMDATEN_NOTE}",
        f"- Floors: {text_value(building, 'etagen')} {STAMMDATEN_NOTE}",
        f"- Elevator: {yes_no(bool_value(building, 'fahrstuhl'))} {STAMMDATEN_NOTE}",
        f"- Construction year: {text_value(building, 'baujahr')} {STAMMDATEN_NOTE}",
        f"- Units indexed: {len(units)} {STAMMDATEN_NOTE}",
        f"- Total unit area: {format_number(total_area)} qm {STAMMDATEN_NOTE}",
        f"- Total MEA: {format_number(total_mea)} {STAMMDATEN_NOTE}",
        "",
    ]


def building_unit_table(units: list[JsonRecord], relationships: Relationships) -> list[str]:
    rows = [
        "## Units",
        "",
        "| ID | No. | Location | Type | Area qm | Rooms | MEA | Owner | Tenant | Source |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for unit in units:
        unit_id = text_value(unit, "id")
        owner_names = ", ".join(
            display_id_name(owner) for owner in relationships.owners_by_unit_id.get(unit_id, [])
        )
        tenant = relationships.tenant_by_unit_id.get(unit_id)
        rows.append(
            "| "
            + " | ".join(
                [
                    link(unit_id, f"units/{unit_id}.md"),
                    md(text_value(unit, "einheit_nr")),
                    md(text_value(unit, "lage")),
                    md(text_value(unit, "typ")),
                    format_number(number_value(unit, "wohnflaeche_qm")),
                    format_number(number_value(unit, "zimmer")),
                    format_number(number_value(unit, "miteigentumsanteil")),
                    md(owner_names or "unassigned"),
                    md(display_id_name(tenant) if tenant else "none"),
                    STAMMDATEN_NOTE,
                ]
            )
            + " |"
        )
    rows.append("")
    return rows


def unit_facts(
    unit: JsonRecord,
    building_id: str,
    owners: list[JsonRecord],
    tenant: JsonRecord | None,
) -> list[str]:
    return [
        "## Unit Facts",
        "",
        f"- Unit ID: {text_value(unit, 'id')} {STAMMDATEN_NOTE}",
        f"- Unit number: {text_value(unit, 'einheit_nr')} {STAMMDATEN_NOTE}",
        f"- Building: {building_id} {STAMMDATEN_NOTE}",
        f"- Location: {text_value(unit, 'lage')} {STAMMDATEN_NOTE}",
        f"- Type: {text_value(unit, 'typ')} {STAMMDATEN_NOTE}",
        f"- Area: {format_number(number_value(unit, 'wohnflaeche_qm'))} qm {STAMMDATEN_NOTE}",
        f"- Rooms: {format_number(number_value(unit, 'zimmer'))} {STAMMDATEN_NOTE}",
        f"- MEA: {format_number(number_value(unit, 'miteigentumsanteil'))} {STAMMDATEN_NOTE}",
        f"- Owner link count: {len(owners)} {STAMMDATEN_NOTE}",
        f"- Current tenant: {display_id_name(tenant) if tenant else 'none'} {STAMMDATEN_NOTE}",
        "",
    ]


def unit_ownership(owners: list[JsonRecord]) -> list[str]:
    rows = ["## Ownership", ""]
    if not owners:
        return [*rows, f"- No owner assignment found {STAMMDATEN_NOTE}", ""]
    rows.extend(
        f"- {display_id_name(owner)}; email {text_value(owner, 'email')}; "
        f"SEV {yes_no(bool_value(owner, 'sev_mandat'))}; "
        f"self-user {yes_no(bool_value(owner, 'selbstnutzer'))} {STAMMDATEN_NOTE}"
        for owner in owners
    )
    rows.append("")
    return rows


def unit_tenancy(tenant: JsonRecord | None) -> list[str]:
    rows = ["## Tenancy", ""]
    if not tenant:
        return [*rows, f"- No tenant assignment found {STAMMDATEN_NOTE}", ""]
    nk_prepayment = format_money(number_value(tenant, "nk_vorauszahlung"))
    rows.extend(
        [
            f"- Tenant: {display_id_name(tenant)} {STAMMDATEN_NOTE}",
            f"- Rent start: {text_value(tenant, 'mietbeginn')} {STAMMDATEN_NOTE}",
            f"- Rent end: {text_value(tenant, 'mietende') or 'open-ended'} {STAMMDATEN_NOTE}",
            f"- Cold rent: {format_money(number_value(tenant, 'kaltmiete'))} {STAMMDATEN_NOTE}",
            f"- NK prepayment: {nk_prepayment} {STAMMDATEN_NOTE}",
            f"- Deposit: {format_money(number_value(tenant, 'kaution'))} {STAMMDATEN_NOTE}",
            "",
        ]
    )
    return rows


def owner_index_table(owners: list[JsonRecord], relationships: Relationships) -> list[str]:
    rows = [
        "## Owner Register",
        "",
        "| ID | Name | Company | Units | City | Email | Self-User | SEV | Beirat | Source |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for owner in owners:
        owner_id = text_value(owner, "id")
        units = ", ".join(id_list(owner, "einheit_ids"))
        rows.append(
            "| "
            + " | ".join(
                [
                    link(owner_id, f"{owner_id}.md"),
                    md(display_name(owner)),
                    md(text_value(owner, "firma")),
                    md(units),
                    md(text_value(owner, "ort")),
                    md(text_value(owner, "email")),
                    md(yes_no(bool_value(owner, "selbstnutzer"))),
                    md(yes_no(bool_value(owner, "sev_mandat"))),
                    md(yes_no(bool_value(owner, "beirat"))),
                    STAMMDATEN_NOTE,
                ]
            )
            + " |"
        )
    rows.append("")
    return rows


def owner_contact(owner: JsonRecord) -> list[str]:
    return [
        "## Contact",
        "",
        f"- Owner ID: {text_value(owner, 'id')} {STAMMDATEN_NOTE}",
        f"- Name: {display_name(owner)} {STAMMDATEN_NOTE}",
        f"- Company: {text_value(owner, 'firma') or 'none'} {STAMMDATEN_NOTE}",
        f"- Address: {address(owner)} {STAMMDATEN_NOTE}",
        f"- Email: {text_value(owner, 'email')} {STAMMDATEN_NOTE}",
        f"- Phone: {text_value(owner, 'telefon')} {STAMMDATEN_NOTE}",
        f"- Language: {text_value(owner, 'sprache')} {STAMMDATEN_NOTE}",
        "",
    ]


def owner_units(units: list[JsonRecord]) -> list[str]:
    rows = [
        "## Units",
        "",
        "| Unit | Building | No. | Location | Type | Area qm | MEA | Source |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for unit in units:
        building_id = text_value(unit, "haus_id")
        unit_id = text_value(unit, "id")
        rows.append(
            "| "
            + " | ".join(
                [
                    link(unit_id, f"../../02_buildings/{building_id}/units/{unit_id}.md"),
                    md(building_id),
                    md(text_value(unit, "einheit_nr")),
                    md(text_value(unit, "lage")),
                    md(text_value(unit, "typ")),
                    format_number(number_value(unit, "wohnflaeche_qm")),
                    format_number(number_value(unit, "miteigentumsanteil")),
                    STAMMDATEN_NOTE,
                ]
            )
            + " |"
        )
    rows.append("")
    return rows


def owner_tenant_links(tenants: list[JsonRecord]) -> list[str]:
    rows = ["## Tenant Links", ""]
    if not tenants:
        return [*rows, f"- No tenant linked to this owner in master data {STAMMDATEN_NOTE}", ""]
    rows.extend(
        [
            "| Tenant | Unit | Rent Start | Cold Rent | NK Prepay | Source |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for tenant in tenants:
        tenant_id = text_value(tenant, "id")
        rows.append(
            "| "
            + " | ".join(
                [
                    link(display_id_name(tenant), f"../mieter/{tenant_id}.md"),
                    md(text_value(tenant, "einheit_id")),
                    md(text_value(tenant, "mietbeginn")),
                    format_money(number_value(tenant, "kaltmiete")),
                    format_money(number_value(tenant, "nk_vorauszahlung")),
                    STAMMDATEN_NOTE,
                ]
            )
            + " |"
        )
    rows.append("")
    return rows


def owner_banking(owner: JsonRecord) -> list[str]:
    return [
        "## Banking And Flags",
        "",
        f"- IBAN: {text_value(owner, 'iban')} {STAMMDATEN_NOTE}",
        f"- BIC: {text_value(owner, 'bic')} {STAMMDATEN_NOTE}",
        f"- Self-user: {yes_no(bool_value(owner, 'selbstnutzer'))} {STAMMDATEN_NOTE}",
        f"- SEV mandate: {yes_no(bool_value(owner, 'sev_mandat'))} {STAMMDATEN_NOTE}",
        f"- Advisory board: {yes_no(bool_value(owner, 'beirat'))} {STAMMDATEN_NOTE}",
        "",
    ]


def tenant_index_table(tenants: list[JsonRecord], relationships: Relationships) -> list[str]:
    rows = [
        "## Tenant Register",
        "",
        "| ID | Name | Unit | Owner | Start | End | Cold Rent | NK Prepay | Deposit | Source |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for tenant in tenants:
        tenant_id = text_value(tenant, "id")
        owner = relationships.owners_by_id.get(text_value(tenant, "eigentuemer_id"))
        rows.append(
            "| "
            + " | ".join(
                [
                    link(tenant_id, f"{tenant_id}.md"),
                    md(display_name(tenant)),
                    md(text_value(tenant, "einheit_id")),
                    md(display_id_name(owner) if owner else text_value(tenant, "eigentuemer_id")),
                    md(text_value(tenant, "mietbeginn")),
                    md(text_value(tenant, "mietende") or "open"),
                    format_money(number_value(tenant, "kaltmiete")),
                    format_money(number_value(tenant, "nk_vorauszahlung")),
                    format_money(number_value(tenant, "kaution")),
                    STAMMDATEN_NOTE,
                ]
            )
            + " |"
        )
    rows.append("")
    return rows


def tenant_contact(tenant: JsonRecord) -> list[str]:
    return [
        "## Contact",
        "",
        f"- Tenant ID: {text_value(tenant, 'id')} {STAMMDATEN_NOTE}",
        f"- Name: {display_name(tenant)} {STAMMDATEN_NOTE}",
        f"- Email: {text_value(tenant, 'email')} {STAMMDATEN_NOTE}",
        f"- Phone: {text_value(tenant, 'telefon')} {STAMMDATEN_NOTE}",
        f"- Language: {text_value(tenant, 'sprache')} {STAMMDATEN_NOTE}",
        "",
    ]


def tenant_tenancy(tenant: JsonRecord, relationships: Relationships) -> list[str]:
    unit_id = text_value(tenant, "einheit_id")
    unit = relationships.units_by_id.get(unit_id)
    owner = relationships.owners_by_id.get(text_value(tenant, "eigentuemer_id"))
    building_id = text_value(unit, "haus_id") if unit else "unknown"
    owner_display = display_id_name(owner) if owner else text_value(tenant, "eigentuemer_id")
    nk_prepayment = format_money(number_value(tenant, "nk_vorauszahlung"))
    return [
        "## Tenancy",
        "",
        f"- Unit: {unit_id} in {building_id} {STAMMDATEN_NOTE}",
        f"- Owner: {owner_display} {STAMMDATEN_NOTE}",
        f"- Rent start: {text_value(tenant, 'mietbeginn')} {STAMMDATEN_NOTE}",
        f"- Rent end: {text_value(tenant, 'mietende') or 'open-ended'} {STAMMDATEN_NOTE}",
        f"- Cold rent: {format_money(number_value(tenant, 'kaltmiete'))} {STAMMDATEN_NOTE}",
        f"- NK prepayment: {nk_prepayment} {STAMMDATEN_NOTE}",
        f"- Deposit: {format_money(number_value(tenant, 'kaution'))} {STAMMDATEN_NOTE}",
        "",
    ]


def tenant_banking(tenant: JsonRecord) -> list[str]:
    return [
        "## Banking",
        "",
        f"- IBAN: {text_value(tenant, 'iban')} {STAMMDATEN_NOTE}",
        f"- BIC: {text_value(tenant, 'bic')} {STAMMDATEN_NOTE}",
        "",
    ]


def provider_index_table(providers: list[JsonRecord]) -> list[str]:
    rows = [
        "## Service-Provider Register",
        "",
        "| ID | Company | Branch | Contact | Email | Monthly Contract | Hourly Rate | Source |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for provider in providers:
        provider_id = text_value(provider, "id")
        rows.append(
            "| "
            + " | ".join(
                [
                    link(provider_id, f"{provider_id}.md"),
                    md(text_value(provider, "firma")),
                    md(text_value(provider, "branche")),
                    md(text_value(provider, "ansprechpartner")),
                    md(text_value(provider, "email")),
                    format_money(number_value(provider, "vertrag_monatlich")),
                    format_money(number_value(provider, "stundensatz")),
                    STAMMDATEN_NOTE,
                ]
            )
            + " |"
        )
    rows.append("")
    return rows


def provider_contact(provider: JsonRecord) -> list[str]:
    return [
        "## Contact",
        "",
        f"- Provider ID: {text_value(provider, 'id')} {STAMMDATEN_NOTE}",
        f"- Company: {text_value(provider, 'firma')} {STAMMDATEN_NOTE}",
        f"- Branch: {text_value(provider, 'branche')} {STAMMDATEN_NOTE}",
        f"- Contact person: {text_value(provider, 'ansprechpartner')} {STAMMDATEN_NOTE}",
        f"- Email: {text_value(provider, 'email')} {STAMMDATEN_NOTE}",
        f"- Phone: {text_value(provider, 'telefon')} {STAMMDATEN_NOTE}",
        f"- Address: {address(provider)} {STAMMDATEN_NOTE}",
        f"- Language: {text_value(provider, 'sprache')} {STAMMDATEN_NOTE}",
        "",
    ]


def provider_billing(provider: JsonRecord) -> list[str]:
    return [
        "## Billing",
        "",
        f"- IBAN: {text_value(provider, 'iban')} {STAMMDATEN_NOTE}",
        f"- BIC: {text_value(provider, 'bic')} {STAMMDATEN_NOTE}",
        f"- VAT ID: {text_value(provider, 'ust_id')} {STAMMDATEN_NOTE}",
        f"- Tax number: {text_value(provider, 'steuernummer')} {STAMMDATEN_NOTE}",
        "",
    ]


def provider_contract(provider: JsonRecord) -> list[str]:
    monthly_fee = format_money(number_value(provider, "vertrag_monatlich"))
    return [
        "## Contract",
        "",
        f"- Monthly fee: {monthly_fee} {STAMMDATEN_NOTE}",
        f"- Hourly rate: {format_money(number_value(provider, 'stundensatz'))} {STAMMDATEN_NOTE}",
        f"- Document style hint: {text_value(provider, 'stil')} {STAMMDATEN_NOTE}",
        "",
    ]


def finance_accounts(liegenschaft: JsonRecord) -> list[str]:
    return [
        "## Accounts",
        "",
        "| Account | Bank | IBAN | BIC | Source |",
        "| --- | --- | --- | --- | --- |",
        f"| WEG account | {md(text_value(liegenschaft, 'weg_bankkonto_bank'))} | "
        f"{md(text_value(liegenschaft, 'weg_bankkonto_iban'))} | "
        f"{md(text_value(liegenschaft, 'weg_bankkonto_bic'))} | {STAMMDATEN_NOTE} |",
        f"| Reserve account | | {md(text_value(liegenschaft, 'ruecklage_iban'))} | "
        f"{md(text_value(liegenschaft, 'ruecklage_bic'))} | {STAMMDATEN_NOTE} |",
        f"| Verwalter account | {md(text_value(liegenschaft, 'verwalter_bank'))} | "
        f"{md(text_value(liegenschaft, 'verwalter_iban'))} | "
        f"{md(text_value(liegenschaft, 'verwalter_bic'))} | {STAMMDATEN_NOTE} |",
        "",
    ]


def finance_rent_roll(tenants: list[JsonRecord], relationships: Relationships) -> list[str]:
    rows = [
        "## Tenant Rent Roll",
        "",
        "| Tenant | Unit | Owner | Cold Rent | NK Prepay | Gross Monthly | Deposit | Source |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for tenant in tenants:
        owner = relationships.owners_by_id.get(text_value(tenant, "eigentuemer_id"))
        gross = number_value(tenant, "kaltmiete") + number_value(tenant, "nk_vorauszahlung")
        rows.append(
            "| "
            + " | ".join(
                [
                    md(display_id_name(tenant)),
                    md(text_value(tenant, "einheit_id")),
                    md(display_id_name(owner) if owner else text_value(tenant, "eigentuemer_id")),
                    format_money(number_value(tenant, "kaltmiete")),
                    format_money(number_value(tenant, "nk_vorauszahlung")),
                    format_money(gross),
                    format_money(number_value(tenant, "kaution")),
                    STAMMDATEN_NOTE,
                ]
            )
            + " |"
        )
    total_cold = sum(number_value(tenant, "kaltmiete") for tenant in tenants)
    total_nk = sum(number_value(tenant, "nk_vorauszahlung") for tenant in tenants)
    total_deposits = sum(number_value(tenant, "kaution") for tenant in tenants)
    rows.extend(
        [
            "",
            f"- Total cold rent: {format_money(total_cold)} {STAMMDATEN_NOTE}",
            f"- Total NK prepayments: {format_money(total_nk)} {STAMMDATEN_NOTE}",
            f"- Total deposits: {format_money(total_deposits)} {STAMMDATEN_NOTE}",
            "",
        ]
    )
    return rows


def finance_owner_flags(owners: list[JsonRecord]) -> list[str]:
    rows = [
        "## Owner Payment Flags",
        "",
        "| Owner | Units | Self-User | SEV Mandate | Beirat | IBAN | Source |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for owner in owners:
        rows.append(
            "| "
            + " | ".join(
                [
                    md(display_id_name(owner)),
                    md(", ".join(id_list(owner, "einheit_ids"))),
                    md(yes_no(bool_value(owner, "selbstnutzer"))),
                    md(yes_no(bool_value(owner, "sev_mandat"))),
                    md(yes_no(bool_value(owner, "beirat"))),
                    md(text_value(owner, "iban")),
                    STAMMDATEN_NOTE,
                ]
            )
            + " |"
        )
    rows.append("")
    return rows


def finance_provider_contracts(providers: list[JsonRecord]) -> list[str]:
    fixed_monthly_total = sum(number_value(p, "vertrag_monatlich") for p in providers)
    rows = [
        "## Provider Contracts",
        "",
        "| Provider | Branch | Monthly Contract | Hourly Rate | Source |",
        "| --- | --- | --- | --- | --- |",
    ]
    for provider in providers:
        rows.append(
            "| "
            + " | ".join(
                [
                    md(display_id_name(provider)),
                    md(text_value(provider, "branche")),
                    format_money(number_value(provider, "vertrag_monatlich")),
                    format_money(number_value(provider, "stundensatz")),
                    STAMMDATEN_NOTE,
                ]
            )
            + " |"
        )
    rows.extend(
        [
            "",
            f"- Fixed monthly provider total: {format_money(fixed_monthly_total)} "
            f"{STAMMDATEN_NOTE}",
            "",
        ]
    )
    return rows


def source_table(source_type: str, source_files: list[SourceFile]) -> list[str]:
    files = [file for file in source_files if file.source_type == source_type]
    rows = [
        f"## {source_type.title()} Files",
        "",
        "| Source ID | Source Path | Norm Path | Hash | Normalized At | Bytes | Source |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    if not files:
        return [*rows, f"| none | none | none | none | none | none | {STAMMDATEN_NOTE} |", ""]
    for file in files:
        rows.append(
            "| "
            + " | ".join(
                [
                    md(file.source_id),
                    md(file.source_path),
                    md(file.relative_path),
                    md(short_hash(file.content_hash)),
                    md(file.normalized_at),
                    md(file.size_bytes),
                    md(file.relative_path),
                ]
            )
            + " |"
        )
    rows.append("")
    return rows


def normalized_bank_index_table(normalize_dir: Path) -> list[str]:
    path = normalize_dir / "base" / "bank" / "bank_index.md"
    if not path.exists():
        return []

    rows = ["## Transactions", ""]
    in_table = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("| id |"):
            rows.append(f"{line.rstrip().rstrip('|').rstrip()} | Source |")
            in_table = True
            continue
        if in_table and line.startswith("| --- |"):
            rows.append(f"{line.rstrip().rstrip('|').rstrip()} | --- |")
            continue
        if in_table and line.startswith("|"):
            rows.append(f"{line.rstrip().rstrip('|').rstrip()} | [^bank_index] |")
            continue
        if in_table:
            break
    rows.append("")
    return rows


def relationship_issues(dataset: ContextDataset, relationships: Relationships) -> list[str]:
    issues: list[str] = []
    for unit in dataset.units:
        building_id = text_value(unit, "haus_id")
        if building_id not in relationships.buildings_by_id:
            issues.append(
                f"Unit {text_value(unit, 'id')} references missing building {building_id}"
            )
    for owner in dataset.owners:
        for unit_id in id_list(owner, "einheit_ids"):
            if unit_id not in relationships.units_by_id:
                issues.append(f"Owner {text_value(owner, 'id')} references missing unit {unit_id}")
    for tenant in dataset.tenants:
        unit_id = text_value(tenant, "einheit_id")
        owner_id = text_value(tenant, "eigentuemer_id")
        if unit_id not in relationships.units_by_id:
            issues.append(f"Tenant {text_value(tenant, 'id')} references missing unit {unit_id}")
        if owner_id not in relationships.owners_by_id:
            issues.append(f"Tenant {text_value(tenant, 'id')} references missing owner {owner_id}")
    return issues


def counts_for(dataset: ContextDataset, source_files: list[SourceFile]) -> dict[str, int]:
    counts = {
        "buildings": len(dataset.buildings),
        "units": len(dataset.units),
        "owners": len(dataset.owners),
        "tenants": len(dataset.tenants),
        "providers": len(dataset.providers),
        "normalized_sources": len(source_files),
    }
    for source_type, count in source_counts(source_files).items():
        counts[f"source_{source_type}"] = count
    return counts


def source_counts(source_files: Iterable[SourceFile]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for file in source_files:
        counts[file.source_type] += 1
    return dict(counts)


def front_matter(name: str, description: str) -> list[str]:
    return [
        "---",
        f"name: {json.dumps(name, ensure_ascii=False)}",
        f"description: {json.dumps(description, ensure_ascii=False)}",
        "---",
        "",
    ]


def section(section_id: str, lines: list[str]) -> list[str]:
    return [
        f"<!-- @section:{section_id} version=0 -->",
        *lines,
        f"<!-- @endsection:{section_id} -->",
        "",
    ]


def provenance_section(provenance: Provenance) -> list[str]:
    return [
        "## Provenance",
        "",
        f"[^stammdaten]: Normalized source `{provenance.normalized_path}`; "
        f"raw source `{provenance.source_path}`; hash `{provenance.content_hash}`; "
        f"normalized at `{provenance.normalized_at}`.",
        "",
    ]


def bank_provenance_section(provenance: Provenance) -> list[str]:
    lines = provenance_section(provenance)
    lines.extend(
        [
            "[^bank_index]: Normalized bank index `normalize/base/bank/bank_index.md`; "
            "one row per transaction from the normalized bank corpus.",
            "",
        ]
    )
    return lines


def recent_event_lines(label: str) -> list[str]:
    return [
        "## Recent Events",
        "",
        f"- {datetime.now(UTC).date().isoformat()}: {label} {STAMMDATEN_NOTE}",
        "",
    ]


def with_human_notes(content: str, human_notes: str) -> str:
    base = content.rstrip()
    notes = human_notes.strip("\n")
    if notes:
        return f"{base}\n\n{HUMAN_NOTES_HEADING}\n{notes}\n"
    return f"{base}\n\n{HUMAN_NOTES_HEADING}\n"


def extract_human_notes(content: str) -> str:
    marker = f"\n{HUMAN_NOTES_HEADING}"
    index = content.find(marker)
    if index == -1 and content.startswith(HUMAN_NOTES_HEADING):
        return content[len(HUMAN_NOTES_HEADING) :].strip("\n")
    if index == -1:
        return ""
    return content[index + len(marker) :].strip("\n")


def normalized_metadata(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    metadata: dict[str, str] = {}
    with path.open("r", encoding="utf-8") as f:
        if f.readline().strip() != "---":
            return metadata
        for line in f:
            if line.strip() == "---":
                break
            key, separator, value = line.partition(":")
            if not separator:
                continue
            metadata[key.strip()] = parse_metadata_value(value.strip())
    return metadata


def parse_metadata_value(value: str) -> str:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return value
    return str(parsed)


def record_value(data: JsonRecord, key: str) -> JsonRecord:
    value = data.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"Expected object at key {key!r}")
    return cast(JsonRecord, value)


def record_list(data: JsonRecord, key: str) -> list[JsonRecord]:
    value = data.get(key)
    if not isinstance(value, list):
        raise ValueError(f"Expected list at key {key!r}")
    return [cast(JsonRecord, item) for item in value if isinstance(item, dict)]


def text_value(record: JsonRecord | None, key: str) -> str:
    if record is None:
        return ""
    value = record.get(key)
    if value is None:
        return ""
    return str(value)


def number_value(record: JsonRecord, key: str) -> float:
    value = record.get(key)
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.replace(",", "."))
        except ValueError:
            return 0.0
    return 0.0


def bool_value(record: JsonRecord, key: str) -> bool:
    return bool(record.get(key))


def id_list(record: JsonRecord, key: str) -> list[str]:
    value = record.get(key)
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def display_name(record: JsonRecord) -> str:
    company = text_value(record, "firma")
    if company:
        return company
    parts = [
        text_value(record, "anrede"),
        text_value(record, "vorname"),
        text_value(record, "nachname"),
    ]
    return " ".join(part for part in parts if part)


def display_id_name(record: JsonRecord | None) -> str:
    if record is None:
        return ""
    name = display_name(record)
    record_id = text_value(record, "id")
    return f"{record_id} {name}" if name else record_id


def address(record: JsonRecord) -> str:
    parts = [
        text_value(record, "strasse"),
        " ".join(part for part in [text_value(record, "plz"), text_value(record, "ort")] if part),
        text_value(record, "land"),
    ]
    return ", ".join(part for part in parts if part)


def yes_no(value: bool) -> str:
    return "yes" if value else "no"


def format_number(value: float) -> str:
    if value.is_integer():
        return str(int(value))
    return f"{value:.2f}".rstrip("0").rstrip(".")


def format_money(value: float) -> str:
    return f"{value:.2f} EUR"


def short_hash(value: str) -> str:
    return value[:12] if value else ""


def link(label: str, target: str) -> str:
    return f"[{md(label)}]({target})"


def md(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def slug(*parts: str) -> str:
    raw = "-".join(part for part in parts if part).lower()
    allowed = []
    for char in raw:
        if char.isalnum():
            allowed.append(char)
        elif char in {"-", "_", " "}:
            allowed.append("-")
    return "-".join(part for part in "".join(allowed).split("-") if part)


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
