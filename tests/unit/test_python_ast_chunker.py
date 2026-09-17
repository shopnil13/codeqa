from pathlib import Path

from codeqa.ingest.chunkers.python_ast import PythonASTChunker

FIXTURES = Path(__file__).parent.parent / "fixtures" / "sample_code"


def test_basic_file_chunks() -> None:
    source = (FIXTURES / "basic.py").read_bytes()
    chunks = PythonASTChunker().chunk_file(FIXTURES / "basic.py", source)

    kinds = {c.kind for c in chunks}
    assert "class_skeleton" in kinds
    assert "method" in kinds
    assert "function" in kinds

    send_chunk = next(c for c in chunks if c.qualified_name == "Client.send")
    assert "def send" in send_chunk.content
    assert send_chunk.docstring == "Send a request."


def test_syntax_error_does_not_crash() -> None:
    source = (FIXTURES / "syntax_error.py").read_bytes()
    chunks = PythonASTChunker().chunk_file(FIXTURES / "syntax_error.py", source)
    assert isinstance(chunks, list)  # tree-sitter degrades, does not raise


def test_empty_file() -> None:
    source = (FIXTURES / "empty.py").read_bytes()
    chunks = PythonASTChunker().chunk_file(FIXTURES / "empty.py", source)
    assert chunks == []
