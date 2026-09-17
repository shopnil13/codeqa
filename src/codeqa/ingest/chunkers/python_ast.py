from pathlib import Path

import tree_sitter_python as tspython
from tree_sitter import Language, Node, Parser

from codeqa.ingest.chunkers.base import Chunk

PY_LANGUAGE = Language(tspython.language())
MAX_CHUNK_CHARS = 4000


def _text(node: Node, source: bytes) -> str:
    return source[node.start_byte : node.end_byte].decode("utf-8", errors="replace")


def _effective_node(node: Node) -> Node:
    """Return the decorated_definition wrapper if present, so decorators are kept."""
    parent = node.parent
    if parent is not None and parent.type == "decorated_definition":
        return parent
    return node


def _signature(node: Node, source: bytes) -> str:
    """Text from node start up to (not including) the body block."""
    body = next((c for c in node.children if c.type == "block"), None)
    end = body.start_byte if body is not None else node.end_byte
    return source[node.start_byte : end].decode("utf-8", errors="replace").rstrip()


def _docstring(node: Node, source: bytes) -> str | None:
    body = next((c for c in node.children if c.type == "block"), None)
    if body is None or not body.children:
        return None
    first = body.children[0]
    if first.type == "expression_statement" and first.children:
        expr = first.children[0]
        if expr.type == "string":
            return _text(expr, source).strip("\"' \n")
    return None


def _split_oversized(chunk: Chunk) -> list[Chunk]:
    if len(chunk.content) <= MAX_CHUNK_CHARS:
        return [chunk]

    lines = chunk.content.splitlines(keepends=True)
    parts: list[Chunk] = []
    current: list[str] = []
    current_len = 0
    part_index = 0

    for line in lines:
        if current_len + len(line) > MAX_CHUNK_CHARS and current:
            parts.append(_make_part(chunk, current, part_index))
            part_index += 1
            current = []
            current_len = 0
        current.append(line)
        current_len += len(line)

    if current:
        parts.append(_make_part(chunk, current, part_index))

    return parts


def _make_part(original: Chunk, lines: list[str], part_index: int) -> Chunk:
    header = f"{original.signature}\n" if original.signature else ""
    content = header + "".join(lines) if part_index > 0 else "".join(lines)
    return Chunk(
        kind=original.kind,
        symbol_name=original.symbol_name,
        qualified_name=original.qualified_name,
        parent_name=original.parent_name,
        signature=original.signature,
        docstring=original.docstring if part_index == 0 else None,
        start_line=original.start_line,
        end_line=original.end_line,
        content=content,
        part_index=part_index,
    )


class PythonASTChunker:
    def chunk_file(self, path: Path, source: bytes) -> list[Chunk]:
        parser = Parser(PY_LANGUAGE)
        tree = parser.parse(source)
        root = tree.root_node

        chunks: list[Chunk] = []
        module_statements: list[Node] = []

        for child in root.children:
            if child.type == "function_definition":
                chunks.extend(self._function_chunk(child, source, parent_name=None))
            elif child.type == "class_definition":
                chunks.extend(self._class_chunks(child, source))
            elif child.type == "decorated_definition":
                def_types = ("function_definition", "class_definition")
                inner = next(
                    (c for c in child.children if c.type in def_types),
                    None,
                )

                if inner is not None and inner.type == "function_definition":
                    chunks.extend(self._function_chunk(inner, source, parent_name=None))
                elif inner is not None:
                    chunks.extend(self._class_chunks(inner, source))
            else:
                module_statements.append(child)

        module_chunk = self._module_chunk(root, module_statements, source)
        if module_chunk is not None:
            chunks.append(module_chunk)

        return chunks

    def _function_chunk(self, node: Node, source: bytes, parent_name: str | None) -> list[Chunk]:
        effective = _effective_node(node)
        name_node = node.child_by_field_name("name")
        symbol_name = _text(name_node, source) if name_node else None
        qualified_name = f"{parent_name}.{symbol_name}" if parent_name else symbol_name

        chunk = Chunk(
            kind="method" if parent_name else "function",
            symbol_name=symbol_name,
            qualified_name=qualified_name,
            parent_name=parent_name,
            signature=_signature(node, source),
            docstring=_docstring(node, source),
            start_line=effective.start_point[0] + 1,
            end_line=effective.end_point[0] + 1,
            content=_text(effective, source),
        )
        return _split_oversized(chunk)

    def _class_chunks(self, node: Node, source: bytes) -> list[Chunk]:
        effective = _effective_node(node)
        name_node = node.child_by_field_name("name")
        class_name = _text(name_node, source) if name_node else None
        body = node.child_by_field_name("body")

        chunks: list[Chunk] = []
        skeleton_lines = [_signature(node, source)]
        docstring = _docstring(node, source)
        if docstring:
            skeleton_lines.append(f'    """{docstring}"""')

        if body is not None:
            for member in body.children:
                if member.type == "function_definition":
                    chunks.extend(self._function_chunk(member, source, parent_name=class_name))
                    method_sig = _signature(member, source)
                    skeleton_lines.append(f"    {method_sig.strip()}: ...")
                elif member.type == "decorated_definition":
                    inner = next(
                        (c for c in member.children if c.type == "function_definition"), None
                    )
                    if inner is not None:
                        chunks.extend(self._function_chunk(inner, source, parent_name=class_name))
                        method_sig = _signature(inner, source)
                        skeleton_lines.append(f"    {method_sig.strip()}: ...")

        skeleton = Chunk(
            kind="class_skeleton",
            symbol_name=class_name,
            qualified_name=class_name,
            parent_name=None,
            signature=_signature(node, source),
            docstring=docstring,
            start_line=effective.start_point[0] + 1,
            end_line=effective.end_point[0] + 1,
            content="\n".join(skeleton_lines),
        )
        chunks.append(skeleton)
        return chunks

    def _module_chunk(self, root: Node, statements: list[Node], source: bytes) -> Chunk | None:
        if not statements:
            return None

        module_types = (
            "import_statement",
            "import_from_statement",
            "expression_statement",
            "assignment",
        )
        relevant = [s for s in statements if s.type in module_types]

        if not relevant:
            return None

        content = "\n".join(_text(s, source) for s in relevant)[:MAX_CHUNK_CHARS]
        docstring = None
        if relevant[0].type == "expression_statement" and relevant[0].children:
            expr = relevant[0].children[0]
            if expr.type == "string":
                docstring = _text(expr, source).strip("\"' \n")

        return Chunk(
            kind="module",
            symbol_name=None,
            qualified_name=None,
            parent_name=None,
            signature=None,
            docstring=docstring,
            start_line=relevant[0].start_point[0] + 1,
            end_line=relevant[-1].end_point[0] + 1,
            content=content,
        )
