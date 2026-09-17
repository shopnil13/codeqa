from dataclasses import dataclass
from pathlib import Path

import tree_sitter_python as tspython
from tree_sitter import Language, Node, Parser

PY_LANGUAGE = Language(tspython.language())


@dataclass
class SymbolEdge:
    source_qualified_name: str
    target_name: str
    kind: str  # "call" | "import"


def _text(node: Node, source: bytes) -> str:
    return source[node.start_byte : node.end_byte].decode("utf-8", errors="replace")


def extract_edges(path: Path, source: bytes) -> list[SymbolEdge]:
    parser = Parser(PY_LANGUAGE)
    tree = parser.parse(source)
    root = tree.root_node

    edges: list[SymbolEdge] = []

    def walk_calls(node: Node, owner: str) -> None:
        for child in node.children:
            if child.type == "call":
                func = child.child_by_field_name("function")
                if func is not None:
                    name = _text(func, source).split(".")[-1]
                    edges.append(SymbolEdge(owner, name, "call"))
            walk_calls(child, owner)

    def walk_defs(node: Node, parent_class: str | None) -> None:
        for child in node.children:
            if child.type == "function_definition":
                name_node = child.child_by_field_name("name")
                name = _text(name_node, source) if name_node else "?"
                qualified = f"{parent_class}.{name}" if parent_class else name
                body = child.child_by_field_name("body")
                if body is not None:
                    walk_calls(body, qualified)
            elif child.type == "class_definition":
                name_node = child.child_by_field_name("name")
                class_name = _text(name_node, source) if name_node else "?"
                body = child.child_by_field_name("body")
                if body is not None:
                    walk_defs(body, class_name)
            elif child.type in ("import_statement", "import_from_statement"):
                for name_node in child.children:
                    if name_node.type in ("dotted_name", "identifier"):
                        edges.append(SymbolEdge("<module>", _text(name_node, source), "import"))
            else:
                walk_defs(child, parent_class)

    walk_defs(root, None)
    return edges
