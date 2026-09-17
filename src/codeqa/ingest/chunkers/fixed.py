from pathlib import Path

from codeqa.ingest.chunkers.base import Chunk

CHUNK_LINES = 60
OVERLAP_LINES = 10


class FixedSizeChunker:
    def chunk_file(self, path: Path, source: bytes) -> list[Chunk]:
        text = source.decode("utf-8", errors="replace")
        lines = text.splitlines()

        chunks: list[Chunk] = []
        start = 0
        part_index = 0
        while start < len(lines):
            end = min(start + CHUNK_LINES, len(lines))
            content = "\n".join(lines[start:end])
            chunks.append(
                Chunk(
                    kind="fixed",
                    symbol_name=None,
                    qualified_name=None,
                    parent_name=None,
                    signature=None,
                    docstring=None,
                    start_line=start + 1,
                    end_line=end,
                    content=content,
                    part_index=part_index,
                )
            )
            if end == len(lines):
                break
            start = end - OVERLAP_LINES
            part_index += 1

        return chunks
