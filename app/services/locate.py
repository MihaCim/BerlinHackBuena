from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.storage.wiki_chunks import WikiChunksStore


@dataclass(frozen=True)
class LocatedSection:
    file: str
    section: str
    body: str
    entity_refs: list[str]
    score: float = 0.0


def locate_sections(
    *,
    wiki_chunks: WikiChunksStore,
    property_id: str,
    entity_ids: list[str],
    query_text: str = "",
    limit: int = 8,
) -> list[LocatedSection]:
    wiki_chunks.build_index()
    found: dict[tuple[str, str], LocatedSection] = {}

    for entity_id in entity_ids:
        for row in wiki_chunks.find_by_entity(property_id, entity_id):
            key = (str(row["file"]), str(row["section"]))
            found[key] = LocatedSection(
                file=str(row["file"]),
                section=str(row["section"]),
                body=str(row["body"]),
                entity_refs=list(row.get("entity_refs") or []),
                score=max(found.get(key, _empty_section()).score, 10.0),
            )
            if len(found) >= limit:
                return list(found.values())[:limit]

    if query_text:
        for row in wiki_chunks.query(query_text, property_id=property_id, limit=limit):
            key = (str(row["file"]), str(row["section"]))
            if key in found:
                continue
            found[key] = LocatedSection(
                file=str(row["file"]),
                section=str(row["section"]),
                body=str(row["body"]),
                entity_refs=list(_refs(row)),
                score=float(row.get("score", 0.0)),
            )
            if len(found) >= limit:
                break

    return list(found.values())[:limit]


def _refs(row: dict[str, Any]) -> list[str]:
    refs = row.get("entity_refs", [])
    if isinstance(refs, list):
        return [str(ref) for ref in refs]
    return []


def _empty_section() -> LocatedSection:
    return LocatedSection(file="", section="", body="", entity_refs=[], score=0.0)
