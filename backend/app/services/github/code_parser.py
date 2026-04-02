"""Tree-sitter-based code parser.

Extracts structured symbol information (classes, functions, imports) from
source files using Tree-sitter's concrete syntax trees. Falls back to
regex-based extraction if Tree-sitter isn't available or the language
isn't supported.
"""

import re
from typing import Optional


class CodeParser:
    """Extracts code symbols from source files using Tree-sitter or fallback regex."""

    def __init__(self) -> None:
        self._ts_available = self._check_tree_sitter()

    def _check_tree_sitter(self) -> bool:
        try:
            import tree_sitter  # noqa: F401
            return True
        except ImportError:
            return False

    def extract_symbols(self, file_path: str, content: str) -> list[dict]:
        """Extract symbols from a source file. Returns list of symbol dicts."""
        ext = "." + file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""

        if not content.strip():
            return []

        # Route to language-specific parser
        if ext == ".py":
            return self._parse_python(file_path, content)
        if ext in (".js", ".jsx"):
            return self._parse_javascript(file_path, content)
        if ext in (".ts", ".tsx"):
            return self._parse_typescript(file_path, content)
        if ext in (".go",):
            return self._parse_go(file_path, content)
        if ext in (".java",):
            return self._parse_java(file_path, content)
        if ext in (".md", ".rst"):
            return self._parse_docs(file_path, content)

        return []

    # ------------------------------------------------------------------
    # Tree-sitter parsers (with regex fallback)
    # ------------------------------------------------------------------

    def _parse_python(self, file_path: str, content: str) -> list[dict]:
        if self._ts_available:
            try:
                return self._ts_parse_python(file_path, content)
            except Exception:
                pass
        return self._regex_parse_python(file_path, content)

    def _ts_parse_python(self, file_path: str, content: str) -> list[dict]:
        import tree_sitter_python as tspython
        from tree_sitter import Language, Parser

        PY_LANGUAGE = Language(tspython.language())
        parser = Parser(PY_LANGUAGE)
        tree = parser.parse(content.encode())
        symbols = []

        def walk(node, depth=0):
            if node.type in ("function_definition", "async_function_definition", "class_definition"):
                name_node = node.child_by_field_name("name")
                name = name_node.text.decode() if name_node else ""
                kind = "class" if node.type == "class_definition" else "function"

                # Extract docstring
                docstring = ""
                body = node.child_by_field_name("body")
                if body and body.child_count > 0:
                    first = body.children[0]
                    if first.type == "expression_statement":
                        for child in first.children:
                            if child.type == "string":
                                docstring = child.text.decode().strip("\"'").strip()

                symbols.append({
                    "name": name,
                    "kind": kind,
                    "file_path": file_path,
                    "line_start": node.start_point[0] + 1,
                    "line_end": node.end_point[0] + 1,
                    "docstring": docstring[:300],
                })

            for child in node.children:
                walk(child, depth + 1)

        walk(tree.root_node)
        return symbols

    def _regex_parse_python(self, file_path: str, content: str) -> list[dict]:
        symbols = []
        lines = content.split("\n")
        fn_re = re.compile(r"^(async\s+)?def\s+(\w+)\s*\(")
        cls_re = re.compile(r"^class\s+(\w+)")

        for i, line in enumerate(lines):
            m = fn_re.match(line)
            if m:
                name = m.group(2)
                docstring = _extract_docstring_after(lines, i)
                symbols.append({"name": name, "kind": "function", "file_path": file_path,
                                 "line_start": i + 1, "line_end": i + 1, "docstring": docstring})
                continue
            m = cls_re.match(line)
            if m:
                symbols.append({"name": m.group(1), "kind": "class", "file_path": file_path,
                                 "line_start": i + 1, "line_end": i + 1, "docstring": ""})
        return symbols

    def _parse_javascript(self, file_path: str, content: str) -> list[dict]:
        symbols = []
        lines = content.split("\n")
        # function declarations and class declarations
        patterns = [
            (re.compile(r"^(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\("), "function"),
            (re.compile(r"^(?:export\s+)?(?:default\s+)?class\s+(\w+)"), "class"),
            (re.compile(r"^(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s*)?\("), "function"),
            (re.compile(r"^(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s+)?function"), "function"),
        ]
        for i, line in enumerate(lines):
            for pattern, kind in patterns:
                m = pattern.match(line.strip())
                if m:
                    symbols.append({"name": m.group(1), "kind": kind, "file_path": file_path,
                                     "line_start": i + 1, "line_end": i + 1, "docstring": ""})
                    break
        return symbols

    def _parse_typescript(self, file_path: str, content: str) -> list[dict]:
        symbols = self._parse_javascript(file_path, content)
        lines = content.split("\n")
        # TypeScript-specific: interfaces and type aliases
        for i, line in enumerate(lines):
            m = re.match(r"^(?:export\s+)?interface\s+(\w+)", line.strip())
            if m:
                symbols.append({"name": m.group(1), "kind": "interface", "file_path": file_path,
                                 "line_start": i + 1, "line_end": i + 1, "docstring": ""})
            m = re.match(r"^(?:export\s+)?type\s+(\w+)\s*=", line.strip())
            if m:
                symbols.append({"name": m.group(1), "kind": "type", "file_path": file_path,
                                 "line_start": i + 1, "line_end": i + 1, "docstring": ""})
        return symbols

    def _parse_go(self, file_path: str, content: str) -> list[dict]:
        symbols = []
        lines = content.split("\n")
        for i, line in enumerate(lines):
            m = re.match(r"^func\s+(?:\(.*?\)\s+)?(\w+)\s*\(", line)
            if m:
                symbols.append({"name": m.group(1), "kind": "function", "file_path": file_path,
                                 "line_start": i + 1, "line_end": i + 1, "docstring": ""})
            m = re.match(r"^type\s+(\w+)\s+struct", line)
            if m:
                symbols.append({"name": m.group(1), "kind": "struct", "file_path": file_path,
                                 "line_start": i + 1, "line_end": i + 1, "docstring": ""})
        return symbols

    def _parse_java(self, file_path: str, content: str) -> list[dict]:
        symbols = []
        lines = content.split("\n")
        cls_re = re.compile(r"(?:public|private|protected|abstract|final|\s)+class\s+(\w+)")
        fn_re = re.compile(r"(?:public|private|protected|static|final|abstract|\s)+\w+\s+(\w+)\s*\(")
        for i, line in enumerate(lines):
            m = cls_re.search(line)
            if m:
                symbols.append({"name": m.group(1), "kind": "class", "file_path": file_path,
                                 "line_start": i + 1, "line_end": i + 1, "docstring": ""})
            elif fn_re.search(line) and "{" in line:
                m2 = fn_re.search(line)
                if m2:
                    symbols.append({"name": m2.group(1), "kind": "function", "file_path": file_path,
                                     "line_start": i + 1, "line_end": i + 1, "docstring": ""})
        return symbols

    def _parse_docs(self, file_path: str, content: str) -> list[dict]:
        """Extract headings from markdown/rst as 'section' symbols."""
        symbols = []
        lines = content.split("\n")
        for i, line in enumerate(lines):
            m = re.match(r"^#{1,3}\s+(.+)$", line)
            if m:
                symbols.append({"name": m.group(1).strip(), "kind": "section",
                                 "file_path": file_path, "line_start": i + 1, "line_end": i + 1,
                                 "docstring": ""})
        return symbols


def _extract_docstring_after(lines: list[str], fn_line: int) -> str:
    """Try to extract a docstring from the lines after a function definition."""
    for i in range(fn_line + 1, min(fn_line + 5, len(lines))):
        stripped = lines[i].strip()
        if stripped.startswith('"""') or stripped.startswith("'''"):
            return stripped.strip('"\'').strip()[:300]
        if stripped:
            break
    return ""
