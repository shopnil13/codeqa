from pathlib import Path

from codeqa.ingest.chunkers.base import Chunk


class MarkdownChunker:
    def chunk_file(self, path: Path, source: bytes) -> list[Chunk]:
        text = source.decode("utf-8", errors="replace")
        lines = text.splitlines()

        chunks: list[Chunk] = []
        current_header = ""
        current_lines: list[str] = []
        start_line = 1

        def flush(end_line: int) -> None:
            if current_lines:
                chunks.append(
                    Chunk(
                        kind="doc_section",
                        symbol_name=current_header or None,
                        qualified_name=current_header or None,
                        parent_name=None,
                        signature=None,
                        docstring=None,
                        start_line=start_line,
                        end_line=end_line,
                        content="\n".join(current_lines),
                    )
                )

        for i, line in enumerate(lines, start=1):
            if line.startswith("#"):
                flush(i - 1)
                current_header = line.lstrip("#").strip()
                current_lines = [line]
                start_line = i
            else:
                current_lines.append(line)

        flush(len(lines))
        return chunks
