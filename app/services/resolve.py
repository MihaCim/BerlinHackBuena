from __future__ import annotations

import re
from dataclasses import dataclass, field
from email.utils import getaddresses
from typing import Any

from app.storage.stammdaten import StammdatenStore

_ENTITY_ID_RE = re.compile(r"\b(?:LIE|HAUS|EH|EIG|MIE|DL)-\d{2,5}\b", re.IGNORECASE)
_SOURCE_ID_RE = re.compile(r"\b(?:EMAIL|INV|LTR|TX)-[A-Z]*-?\d{3,6}\b", re.IGNORECASE)
_EMAIL_RE = re.compile(r"[\w.!#$%&'*+/=?^`{|}~-]+@[\w.-]+\.[A-Za-z]{2,}")
_IBAN_RE = re.compile(r"\b[A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]){11,30}\b")


@dataclass(frozen=True)
class ResolvedEntity:
    id: str
    role: str
    source: str
    data: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ResolutionResult:
    property_id: str
    entities: list[ResolvedEntity]
    mentioned_ids: list[str]
    source_ids: list[str]
    unresolved_ids: list[str]

    @property
    def entity_ids(self) -> list[str]:
        ids = [entity.id for entity in self.entities]
        ids.extend(self.mentioned_ids)
        return _dedupe(ids)


def resolve_context(
    *,
    normalized_text: str,
    stammdaten: StammdatenStore,
    property_id: str = "LIE-001",
) -> ResolutionResult:
    entities: list[ResolvedEntity] = []
    unresolved_ids: list[str] = []

    for email in _emails(normalized_text):
        row = stammdaten.find_entity_by_email(email)
        if row is not None:
            entities.extend(_entity_chain(row, source="email", stammdaten=stammdaten))

    for iban in _ibans(normalized_text):
        row = stammdaten.find_entity_by_iban(iban)
        if row is not None:
            entities.extend(_entity_chain(row, source="iban", stammdaten=stammdaten))

    mentioned_ids = []
    for entity_id in _entity_ids(normalized_text):
        row = stammdaten.find_entity_by_id(entity_id)
        if row is None:
            unresolved_ids.append(entity_id)
            continue
        mentioned_ids.append(entity_id)
        entities.extend(_entity_chain(row, source="mentioned_id", stammdaten=stammdaten))

    return ResolutionResult(
        property_id=property_id,
        entities=_dedupe_entities(entities),
        mentioned_ids=_dedupe(mentioned_ids),
        source_ids=_source_ids(normalized_text),
        unresolved_ids=_dedupe(unresolved_ids),
    )


def _emails(text: str) -> list[str]:
    raw_addresses = _EMAIL_RE.findall(text)
    parsed = [email for _, email in getaddresses(raw_addresses) if email]
    return _dedupe([email.lower() for email in parsed or raw_addresses])


def _ibans(text: str) -> list[str]:
    return _dedupe(match.group(0).replace(" ", "").upper() for match in _IBAN_RE.finditer(text))


def _entity_ids(text: str) -> list[str]:
    return _dedupe(match.group(0).upper() for match in _ENTITY_ID_RE.finditer(text))


def _source_ids(text: str) -> list[str]:
    return _dedupe(match.group(0).upper() for match in _SOURCE_ID_RE.finditer(text))


def _entity_chain(
    row: dict[str, Any],
    *,
    source: str,
    stammdaten: StammdatenStore,
) -> list[ResolvedEntity]:
    entities = [_entity_from_row(row, source)]
    for related_field in ("einheit_id", "eigentuemer_id", "haus_id"):
        related_id = row.get(related_field)
        if not isinstance(related_id, str) or not related_id:
            continue
        related = stammdaten.find_entity_by_id(related_id)
        if related is not None:
            entities.extend(_entity_chain(related, source=source, stammdaten=stammdaten))
    for unit_id in row.get("einheit_ids") or []:
        if not isinstance(unit_id, str):
            continue
        related = stammdaten.find_entity_by_id(unit_id)
        if related is not None:
            entities.extend(_entity_chain(related, source=source, stammdaten=stammdaten))
    return entities


def _entity_from_row(row: dict[str, Any], source: str) -> ResolvedEntity:
    entity_id = str(row["id"])
    role = str(row.get("role") or _role_from_id(entity_id))
    return ResolvedEntity(id=entity_id, role=role, source=source, data=row)


def _role_from_id(entity_id: str) -> str:
    prefix = entity_id.split("-", 1)[0].lower()
    return {
        "lie": "liegenschaft",
        "haus": "gebaeude",
        "eh": "einheit",
        "eig": "eigentuemer",
        "mie": "mieter",
        "dl": "dienstleister",
    }.get(prefix, "entity")


def _dedupe(values: list[str] | Any) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        text = str(value)
        if text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out


def _dedupe_entities(entities: list[ResolvedEntity]) -> list[ResolvedEntity]:
    seen: set[str] = set()
    out: list[ResolvedEntity] = []
    for entity in entities:
        if entity.id in seen:
            continue
        seen.add(entity.id)
        out.append(entity)
    return out
