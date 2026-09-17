import hashlib
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pathspec

from codeqa.config import get_settings

VENDORED_DIRS = {
    "node_modules",
    ".venv",
    "venv",
    "dist",
    "build",
    ".git",
    "__pycache__",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
}
SECRET_PATTERNS = (".env", ".pem", ".key", "credentials.json")
BINARY_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".pdf",
    ".zip",
    ".tar",
    ".gz",
    ".so",
    ".dylib",
    ".dll",
    ".exe",
    ".woff",
    ".woff2",
    ".ttf",
}


@dataclass
class WalkedFile:
    path: Path
    relative_path: str
    content_hash: str
    size_bytes: int


def _load_gitignore(root: Path) -> pathspec.PathSpec:  # type: ignore[type-arg]
    gitignore = root / ".gitignore"
    lines = gitignore.read_text().splitlines() if gitignore.exists() else []
    return pathspec.PathSpec.from_lines("gitwildmatch", lines)


def _looks_like_secret(name: str) -> bool:
    return any(name == p or name.endswith(p) for p in SECRET_PATTERNS)


def walk_repository(root: Path) -> Iterator[WalkedFile]:
    settings = get_settings()
    max_size = settings.max_file_size_mb * 1024 * 1024
    spec = _load_gitignore(root)

    for path in root.rglob("*"):
        if not path.is_file():
            continue

        relative = path.relative_to(root)
        rel_str = str(relative)

        if any(part in VENDORED_DIRS for part in relative.parts):
            continue
        if spec.match_file(rel_str):
            continue
        if _looks_like_secret(path.name):
            continue
        if path.suffix.lower() in BINARY_SUFFIXES:
            continue

        try:
            size = path.stat().st_size
        except OSError:
            continue
        if size > max_size:
            continue

        try:
            data = path.read_bytes()
        except OSError:
            continue
        if b"\x00" in data[:8000]:
            continue  # binary heuristic

        content_hash = hashlib.sha256(data).hexdigest()
        yield WalkedFile(
            path=path, relative_path=rel_str, content_hash=content_hash, size_bytes=size
        )
