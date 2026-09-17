from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass
class Chunk:
    kind: str  # "function" | "method" | "class_skeleton" | "module"
    symbol_name: str | None
    qualified_name: str | None
    parent_name: str | None
    signature: str | None
    docstring: str | None
    start_line: int
    end_line: int
    content: str
    part_index: int = 0
    token_count: int = 0

    def __post_init__(self) -> None:
        if not self.token_count:
            self.token_count = max(1, len(self.content) // 4)


class Chunker(Protocol):
    def chunk_file(self, path: Path, source: bytes) -> list[Chunk]: ...
