#!/usr/bin/env python3
"""Extract issue dependency DAG from gh issue list JSON.

Usage:
    gh issue list --json number,title,body | python scripts/issue_dag.py
    python scripts/issue_dag.py issues.json
    python scripts/issue_dag.py issues.json --png
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_EXPLICIT = re.compile(r"(?:blocked by|depends on|requires)\s+#(\d+)", re.IGNORECASE)
_BARE_REF = re.compile(r"#(\d+)")


def _escape_label(text: str) -> str:
    """Escape backslash then double-quote for DOT / Mermaid label strings."""
    return text.replace("\\", "\\\\").replace('"', '\\"')


def extract_edges(issues: list[dict]) -> set[tuple[int, int]]:
    """Return directed edges (src, dst) where src depends on dst."""
    numbers = {issue["number"] for issue in issues}
    edges: set[tuple[int, int]] = set()
    for issue in issues:
        src = issue["number"]
        body = issue.get("body") or ""
        explicit_refs: set[int] = set()
        for m in _EXPLICIT.finditer(body):
            ref = int(m.group(1))
            if ref != src and ref in numbers:
                explicit_refs.add(ref)
                edges.add((src, ref))
        for m in _BARE_REF.finditer(body):
            ref = int(m.group(1))
            if ref != src and ref in numbers and ref not in explicit_refs:
                edges.add((src, ref))
    return edges


def build_dot(issues: list[dict], edges: set[tuple[int, int]]) -> str:
    lines = ["digraph issues {", "    rankdir=LR;"]
    for issue in sorted(issues, key=lambda i: i["number"]):
        number = issue["number"]
        label = _escape_label(issue.get("title", ""))
        lines.append(f'    {number} [label="#{number}: {label}"];')
    for src, dst in sorted(edges):
        lines.append(f"    {src} -> {dst};")
    lines.append("}")
    return "\n".join(lines)


def build_mmd(issues: list[dict], edges: set[tuple[int, int]]) -> str:
    lines = ["flowchart LR"]
    for issue in sorted(issues, key=lambda i: i["number"]):
        number = issue["number"]
        label = _escape_label(issue.get("title", ""))
        lines.append(f'    i{number}["#{number}: {label}"]')
    for src, dst in sorted(edges):
        lines.append(f"    i{src} --> i{dst}")
    return "\n".join(lines)


def render_png(dot_path: Path, png_path: Path) -> None:
    """Render dot_path to png_path via graphviz dot.

    Exit codes:
      1  - graphviz dot command not found (FileNotFoundError)
      N  - dot exited with non-zero code N
    """
    import subprocess

    try:
        result = subprocess.run(
            ["dot", "-Tpng", str(dot_path), "-o", str(png_path)],
            capture_output=True,
        )
    except FileNotFoundError:
        print(
            "error: graphviz `dot` command not found."
            " Install graphviz (e.g. `apt install graphviz` or `brew install graphviz`)"
            " and retry.",
            file=sys.stderr,
        )
        sys.exit(1)

    if result.returncode == 0:
        print(f"Written: {png_path}")
        return

    print(f"graphviz error: {result.stderr.decode()}", file=sys.stderr)
    sys.exit(result.returncode)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate issue dependency DAG from gh issue list JSON"
    )
    parser.add_argument("input", nargs="?", help="JSON file path (default: stdin)")
    parser.add_argument("--out", default=".", help="Output directory (default: current dir)")
    parser.add_argument(
        "--png",
        action="store_true",
        help="Also render dag.png via graphviz dot (requires graphviz installed)",
    )
    args = parser.parse_args()

    if args.input:
        data = json.loads(Path(args.input).read_text())
    else:
        data = json.load(sys.stdin)

    issues = data if isinstance(data, list) else []
    edges = extract_edges(issues)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    dot_path = out / "dag.dot"
    dot_path.write_text(build_dot(issues, edges))
    print(f"Written: {dot_path}")

    mmd_path = out / "dag.mmd"
    mmd_path.write_text(build_mmd(issues, edges))
    print(f"Written: {mmd_path}")

    if args.png:
        render_png(dot_path, out / "dag.png")


if __name__ == "__main__":
    main()
