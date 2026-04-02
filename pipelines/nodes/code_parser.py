"""
RocketRide custom node: Parse source code files and extract symbols.

Actions:
  extract_symbols  — parse a list of files (from enumerate_repo output) and
                     return function/class/module symbols plus docstrings.
                     Uses ast for Python, regex heuristics for other languages.
"""

import ast
import json
import os
import re
import sys
import urllib.request
from typing import Any


# ---------------------------------------------------------------------------
# Per-language symbol extraction
# ---------------------------------------------------------------------------

def _extract_python(content: str, path: str) -> list[dict]:
    symbols = []
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            doc = ast.get_docstring(node) or ""
            symbols.append({
                "kind": "class" if isinstance(node, ast.ClassDef) else "function",
                "name": node.name,
                "file": path,
                "line": node.lineno,
                "docstring": doc[:500],
            })
    return symbols


_TS_FUNC = re.compile(
    r"(?:export\s+)?(?:async\s+)?function\s+(\w+)|"
    r"(?:export\s+)?(?:abstract\s+)?class\s+(\w+)|"
    r"(?:export\s+)?(?:const|let)\s+(\w+)\s*[:=].*?(?:=>|\bfunction\b)",
    re.MULTILINE,
)

_GO_FUNC = re.compile(r"^func(?:\s+\(\w+\s+\*?\w+\))?\s+(\w+)\s*\(", re.MULTILINE)
_GO_TYPE = re.compile(r"^type\s+(\w+)\s+(?:struct|interface)", re.MULTILINE)


def _extract_generic(content: str, path: str, lang: str) -> list[dict]:
    symbols = []
    if lang in ("ts", "tsx", "js", "jsx"):
        for m in _TS_FUNC.finditer(content):
            name = m.group(1) or m.group(2) or m.group(3)
            if name:
                symbols.append({"kind": "symbol", "name": name, "file": path, "line": 0, "docstring": ""})
    elif lang == "go":
        for m in _GO_FUNC.finditer(content):
            symbols.append({"kind": "function", "name": m.group(1), "file": path, "line": 0, "docstring": ""})
        for m in _GO_TYPE.finditer(content):
            symbols.append({"kind": "class", "name": m.group(1), "file": path, "line": 0, "docstring": ""})
    return symbols


def _lang_for(path: str) -> str:
    return os.path.splitext(path)[1].lstrip(".").lower()


def _parse_file(content: str, path: str) -> list[dict]:
    lang = _lang_for(path)
    if lang == "py":
        return _extract_python(content, path)
    return _extract_generic(content, path, lang)


# ---------------------------------------------------------------------------
# Action: extract_symbols
# ---------------------------------------------------------------------------

def _fetch_file(owner: str, repo: str, path: str, token: str) -> str:
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
    import base64
    return base64.b64decode(data["content"]).decode("utf-8", errors="replace")


def extract_symbols(payload: dict) -> dict:
    owner = payload.get("owner", "")
    repo = payload.get("repo", "")
    files: list[dict] = payload.get("files", [])
    token = os.environ.get("GITHUB_ACCESS_TOKEN", "")
    max_symbols = payload.get("max_symbols", 2000)

    all_symbols: list[dict] = []
    errors: list[str] = []

    for file_info in files:
        path = file_info["path"]
        lang = _lang_for(path)
        # Only parse code files (skip data/config files for symbol extraction)
        if lang not in ("py", "ts", "tsx", "js", "jsx", "go", "java", "rs"):
            continue
        try:
            content = _fetch_file(owner, repo, path, token)
            symbols = _parse_file(content, path)
            all_symbols.extend(symbols)
        except Exception as exc:
            errors.append(f"{path}: {exc}")
        if len(all_symbols) >= max_symbols:
            break

    return {
        "symbols": all_symbols[:max_symbols],
        "symbol_count": len(all_symbols),
        "errors": errors[:20],
    }


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def main() -> None:
    payload = json.loads(sys.stdin.read())
    action = payload.get("action", "extract_symbols")

    if action == "extract_symbols":
        result = extract_symbols(payload)
    else:
        raise ValueError(f"Unknown action: {action}")

    print(json.dumps(result))


if __name__ == "__main__":
    main()
