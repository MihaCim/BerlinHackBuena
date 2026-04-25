from __future__ import annotations

import re
from pathlib import Path

from .ai import answer_with_gemini
from .utils import read_text


def answer_from_context(context_path: Path, question: str, use_ai: bool = False) -> str:
    text = read_text(context_path)
    evidence = retrieve_evidence(text, question)
    if not evidence:
        return "I could not find enough context to answer that from the compiled property file."

    ai_answer = answer_with_gemini(question, evidence, use_ai=use_ai)
    if ai_answer and not ai_answer.startswith("AI answer failed safely:"):
        return ai_answer

    fallback = synthesize_answer(question, evidence)
    if ai_answer:
        return f"{fallback}\n\nNote: {ai_answer}"
    return fallback


def retrieve_evidence(text: str, question: str) -> list[dict[str, str]]:
    question_terms = {term.lower() for term in re.findall(r"[A-Za-z0-9_-]{3,}", question)}
    scored: list[tuple[int, str, str]] = []
    for title, body in split_sections(text):
        clean = clean_body(body)
        haystack = f"{title} {clean}".lower()
        score = sum(1 for term in question_terms if term in haystack)
        score += intent_boost(question.lower(), title)
        if score:
            scored.append((score, title, clean))
    scored.sort(reverse=True, key=lambda item: item[0])
    return [{"title": title, "body": trim_lines(body, 24)} for _, title, body in scored[:5]]


def intent_boost(question: str, title: str) -> int:
    title_lower = title.lower()
    boosts = [
        (("risk", "anomal", "review", "unresolved", "financial", "unpaid"), ("risks", "invoices", "financial"), 6),
        (("owner", "owns", "eigentuemer", "unit", "we ", "eh-"), ("owners", "buildings", "tenants"), 5),
        (("tenant", "rent", "kaution", "deposit", "mieter"), ("tenants", "recent communications", "open operational"), 5),
        (("provider", "vendor", "service", "contractor", "dienstleister"), ("service providers", "invoices"), 5),
        (("topic", "open", "issue", "maintenance", "heating", "water", "damage"), ("open operational", "recent communications", "timeline"), 5),
        (("payment", "invoice", "paid", "reconcile"), ("invoices", "financial", "risks"), 5),
    ]
    score = 0
    for keywords, titles, value in boosts:
        if any(keyword in question for keyword in keywords) and any(part in title_lower for part in titles):
            score += value
    return score


def synthesize_answer(question: str, evidence: list[dict[str, str]]) -> str:
    question_lower = question.lower()
    if any(word in question_lower for word in ("risk", "anomal", "review", "unresolved", "financial", "unpaid")):
        return answer_financial(evidence)
    if any(word in question_lower for word in ("owner", "owns", "unit", "we ", "eh-")):
        return answer_owner_unit(question, evidence)
    if any(word in question_lower for word in ("provider", "vendor", "service", "contractor")):
        return answer_service_provider(evidence)
    if any(word in question_lower for word in ("topic", "open", "issue", "maintenance", "heating", "water", "damage")):
        return answer_topics(evidence)
    return answer_general(evidence)


def answer_financial(evidence: list[dict[str, str]]) -> str:
    lines = evidence_lines(evidence, ("needs review", "unmatched", "not-yet-paid", "anomaly", "review queue"))
    if not lines:
        return answer_general(evidence)
    top = lines[:8]
    return (
        "The main financial attention items are invoices that still need review, mostly because no matching bank transaction was found. "
        f"I found {len(lines)} visible review lines in the retrieved context. The first items are:\n\n"
        + "\n".join(f"- {clean_table_line(line)}" for line in top)
    )


def answer_owner_unit(question: str, evidence: list[dict[str, str]]) -> str:
    target = extract_unit(question)
    owner_lines = [line for line in evidence_lines(evidence, ("| EIG-",)) if line.startswith("| EIG-")]
    unit_lines = [line for line in evidence_lines(evidence, ("| EH-",)) if line.startswith("| EH-")]
    if target:
        matching_owner = [line for line in owner_lines if target in line]
        matching_unit = [line for line in unit_lines if target in line]
        if matching_owner or matching_unit:
            parts = [clean_table_line(line) for line in matching_owner[:3] + matching_unit[:3]]
            return f"For `{target}`, the compiled context shows:\n\n" + "\n".join(f"- {part}" for part in parts)
    if owner_lines:
        return "The owner section maps each `EIG-*` owner to their unit IDs. A few examples:\n\n" + "\n".join(
            f"- {clean_table_line(line)}" for line in owner_lines[:6]
        )
    return answer_general(evidence)


def answer_service_provider(evidence: list[dict[str, str]]) -> str:
    provider_lines = evidence_lines(evidence, ("| DL-",))
    if not provider_lines:
        return answer_general(evidence)
    return "The main service providers are listed with their responsibility, contract basis, invoice count, and contact. Examples:\n\n" + "\n".join(
        f"- {clean_table_line(line)}" for line in provider_lines[:8]
    )


def answer_topics(evidence: list[dict[str, str]]) -> str:
    topic_lines = evidence_lines(evidence, ("### TOPIC-", "- Summary:", "- Priority:", "- Latest update:"))
    if not topic_lines:
        return answer_general(evidence)
    return "The active operational context is concentrated in these retrieved topic details:\n\n" + "\n".join(
        f"- {line.strip()}" for line in topic_lines[:12]
    )


def answer_general(evidence: list[dict[str, str]]) -> str:
    title = evidence[0]["title"]
    lines = [line for line in evidence[0]["body"].splitlines() if line.strip()][:10]
    return f"The most relevant section is `{title}`. In plain terms:\n\n" + "\n".join(
        f"- {clean_table_line(line)}" for line in lines if not is_table_separator(line)
    )


def split_sections(text: str) -> list[tuple[str, str]]:
    pattern = re.compile(r"^## (?P<title>.+?)\n(?P<body>.*?)(?=^## |\Z)", re.S | re.M)
    return [(match.group("title").strip(), match.group("body").strip()) for match in pattern.finditer(text)]


def format_body(body: str, max_lines: int = 18) -> str:
    return trim_lines(clean_body(body), max_lines)


def clean_body(body: str) -> str:
    return re.sub(r"<!--.*?-->", "", body, flags=re.S).strip()


def trim_lines(body: str, max_lines: int = 18) -> str:
    clean = re.sub(r"<!--.*?-->", "", body, flags=re.S)
    lines = [line.rstrip() for line in clean.splitlines() if line.strip()]
    if len(lines) <= max_lines:
        return "\n".join(lines)
    return "\n".join(lines[:max_lines] + ["..."])


def evidence_lines(evidence: list[dict[str, str]], needles: tuple[str, ...]) -> list[str]:
    lines: list[str] = []
    seen: set[str] = set()
    for item in evidence:
        for line in item["body"].splitlines():
            if is_table_separator(line):
                continue
            lowered = line.lower()
            normalized = re.sub(r"\s+", " ", line.strip())
            if normalized in seen:
                continue
            if any(needle.lower() in lowered for needle in needles):
                seen.add(normalized)
                lines.append(line.strip())
    return lines


def clean_table_line(line: str) -> str:
    stripped = line.strip()
    if "|" not in stripped:
        return stripped.lstrip("- ").strip()
    cells = [cell.strip(" `") for cell in stripped.strip("|").split("|")]
    cells = [cell for cell in cells if cell and not set(cell) <= {"-", ":"}]
    return "; ".join(cells)


def is_table_separator(line: str) -> bool:
    stripped = line.strip().replace("|", "").replace(" ", "")
    return bool(stripped) and set(stripped) <= {"-", ":"}


def extract_unit(question: str) -> str:
    match = re.search(r"\b(EH-\d{3})\b", question, flags=re.I)
    if match:
        return match.group(1).upper()
    match = re.search(r"\bWE\s*(\d{1,2})\b", question, flags=re.I)
    if match:
        return f"EH-{int(match.group(1)):03d}"
    return ""
