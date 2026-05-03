from __future__ import annotations

import difflib
import re
from dataclasses import dataclass

USER_BLOCK_RE = re.compile(r"<user\b[^>]*>.*?</user>", flags=re.IGNORECASE | re.DOTALL)


@dataclass(frozen=True)
class GuardResult:
    ok: bool
    reason: str


def extract_user_blocks(markdown: str) -> list[str]:
    return USER_BLOCK_RE.findall(markdown)


def validate_human_authority(before: str, after: str) -> GuardResult:
    if extract_user_blocks(before) != extract_user_blocks(after):
        return GuardResult(False, "Blocked because protected <user> blocks changed.")
    return GuardResult(True, "Protected <user> blocks preserved.")


def unified_diff(before: str, after: str, fromfile: str = "before.md", tofile: str = "after.md") -> str:
    return "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=fromfile,
            tofile=tofile,
        )
    )


def sanitize_agent_markdown(value: str) -> str:
    return (
        value.replace("<!--", "< !--")
        .replace("-->", "-- >")
        .replace("<user", "< user")
        .replace("</user>", "</ user>")
        .strip()
    )
