from __future__ import annotations

from pathlib import Path, PurePosixPath

_WIKI_PREFIX_PARTS = 2


def normalize_property_file(path: str, *, property_id: str) -> str:
    pure = PurePosixPath(path.replace("\\", "/"))
    if pure.is_absolute():
        raise ValueError("patch file path must be relative")

    parts = pure.parts
    if len(parts) >= _WIKI_PREFIX_PARTS and parts[0] == "wiki":
        if parts[1] != property_id:
            raise ValueError("patch file path targets a different property")
        pure = PurePosixPath(*parts[2:])
    elif parts and parts[0].startswith("LIE-"):
        if parts[0] != property_id:
            raise ValueError("patch file path targets a different property")
        pure = PurePosixPath(*parts[1:])

    if not pure.parts or any(part in {"", ".", ".."} for part in pure.parts):
        raise ValueError("patch file path must stay inside the property")
    return pure.as_posix()


def property_file_path(property_root: Path, path: str) -> Path:
    relative = normalize_property_file(path, property_id=property_root.name)
    root = property_root.resolve(strict=False)
    candidate = property_root / relative
    resolved = candidate.resolve(strict=False)
    if not resolved.is_relative_to(root):
        raise ValueError("patch file path escapes the property")
    return candidate
