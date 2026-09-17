from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from codeqa.ingest.chunkers.python_ast import PythonASTChunker

app = typer.Typer()
console = Console()


@app.command()
def chunk(path: Path, limit: int = 20) -> None:
    """Chunk a single Python file and print the results for eyeballing."""

    source = path.read_bytes()
    chunker = PythonASTChunker()
    chunks = chunker.chunk_file(path, source)

    table = Table(title=f"Chunks in {path}")
    table.add_column("kind")
    table.add_column("qualified_name")
    table.add_column("lines")
    table.add_column("tokens")

    for c in chunks[:limit]:
        table.add_row(
            c.kind, c.qualified_name or "-", f"{c.start_line}-{c.end_line}", str(c.token_count)
        )

    console.print(table)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
