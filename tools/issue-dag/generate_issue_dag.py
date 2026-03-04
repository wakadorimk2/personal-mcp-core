#!/usr/bin/env python3
"""Fetch GitHub issue dependencies and generate a DOT graph."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_OWNER = "wakadorimk2"
REPO_NAME = "personal-mcp-core"
ISSUE_NUMBERS = [70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80]
OUTPUT_DIR = Path(__file__).resolve().parent
ISSUES_JSON_PATH = OUTPUT_DIR / "issues.json"
DOT_PATH = OUTPUT_DIR / "issue_dag.dot"
SVG_PATH = OUTPUT_DIR / "issue_dag.svg"
PNG_PATH = OUTPUT_DIR / "issue_dag.png"
MAX_LABEL_TITLE_LENGTH = 52
FONT_ENV_VAR = "ISSUE_DAG_FONTNAME"
DEFAULT_FONT_NAME = "Noto Sans CJK JP"


def run_command(args: list[str]) -> str:
    result = subprocess.run(args, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or f"command failed: {' '.join(args)}")
    return result.stdout


def build_graphql_query() -> str:
    issue_queries = []
    for number in ISSUE_NUMBERS:
        issue_queries.append(
            f"""
      i{number}: issue(number: {number}) {{
        number
        title
        blockedBy(first: 20) {{
          nodes {{
            number
            title
          }}
        }}
        blocking(first: 20) {{
          nodes {{
            number
            title
          }}
        }}
      }}""".rstrip()
        )

    joined_issues = "\n".join(issue_queries)
    return f"""query {{
  repository(owner: "{REPO_OWNER}", name: "{REPO_NAME}") {{
{joined_issues}
  }}
}}"""


def fetch_issue_data() -> dict:
    query = build_graphql_query()
    raw_output = run_command(["gh", "api", "graphql", "-f", f"query={query}"])
    payload = json.loads(raw_output)
    return payload


def normalize_issues(payload: dict) -> list[dict]:
    repository = payload["data"]["repository"]
    issues = []
    for number in ISSUE_NUMBERS:
        issue = repository[f"i{number}"]
        issues.append(
            {
                "number": issue["number"],
                "title": issue["title"],
                "blockedBy": sorted(issue["blockedBy"]["nodes"], key=lambda item: item["number"]),
                "blocking": sorted(issue["blocking"]["nodes"], key=lambda item: item["number"]),
            }
        )
    return issues


def write_issues_json(issues: list[dict]) -> None:
    data = {
        "repo": f"{REPO_OWNER}/{REPO_NAME}",
        "issue_numbers": ISSUE_NUMBERS,
        "issues": issues,
    }
    ISSUES_JSON_PATH.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def build_edges(issues: list[dict]) -> list[tuple[int, int]]:
    issue_set = set(ISSUE_NUMBERS)
    edges: set[tuple[int, int]] = set()

    for issue in issues:
        current = issue["number"]
        for blocked_issue in issue["blocking"]:
            target = blocked_issue["number"]
            if target in issue_set:
                edges.add((current, target))
        for blocker in issue["blockedBy"]:
            source = blocker["number"]
            if source in issue_set:
                edges.add((source, current))

    return sorted(edges)


def find_cycle(edges: list[tuple[int, int]]) -> list[int] | None:
    adjacency = {number: [] for number in ISSUE_NUMBERS}
    for source, target in edges:
        adjacency[source].append(target)

    for number in adjacency:
        adjacency[number].sort()

    unvisited = 0
    visiting = 1
    visited = 2
    state = {number: unvisited for number in ISSUE_NUMBERS}
    stack: list[int] = []

    def dfs(node: int) -> list[int] | None:
        state[node] = visiting
        stack.append(node)
        for neighbor in adjacency[node]:
            if state[neighbor] == unvisited:
                cycle = dfs(neighbor)
                if cycle:
                    return cycle
            elif state[neighbor] == visiting:
                cycle_start = stack.index(neighbor)
                return stack[cycle_start:] + [neighbor]
        stack.pop()
        state[node] = visited
        return None

    for node in ISSUE_NUMBERS:
        if state[node] == unvisited:
            cycle = dfs(node)
            if cycle:
                return cycle

    return None


def shorten_title(title: str) -> str:
    compact = " ".join(title.split())
    if len(compact) <= MAX_LABEL_TITLE_LENGTH:
        return compact
    return compact[: MAX_LABEL_TITLE_LENGTH - 3].rstrip() + "..."


def escape_dot_label(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def resolve_font_name() -> str:
    return os.environ.get(FONT_ENV_VAR, DEFAULT_FONT_NAME)


def warn_if_font_missing() -> None:
    font_name = resolve_font_name()
    if shutil.which("fc-match") is None:
        return

    result = subprocess.run(
        ["fc-match", font_name],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return

    matched_font = result.stdout.strip()
    if font_name not in matched_font:
        print(
            f"Warning: requested font '{font_name}' was not matched by fontconfig.",
            file=sys.stderr,
        )
        print(
            "Install a Japanese font such as 'fonts-noto-cjk' or override "
            f"{FONT_ENV_VAR} to a font that is already installed.",
            file=sys.stderr,
        )


def build_dot(issues: list[dict], edges: list[tuple[int, int]]) -> str:
    font_name = escape_dot_label(resolve_font_name())
    lines = [
        "digraph issue_dag {",
        (
            '  graph [charset="UTF-8", rankdir=LR, label="Issue dependency DAG", '
            f'labelloc=t, fontsize=18, fontname="{font_name}"];'
        ),
        f'  node [shape=box, style="rounded", fontname="{font_name}"];',
        f'  edge [fontname="{font_name}"];',
        "",
        "  // A -> B means A blocks B.",
    ]

    for issue in issues:
        node_id = f"issue_{issue['number']}"
        label = f"#{issue['number']} {shorten_title(issue['title'])}"
        lines.append(f'  {node_id} [label="{escape_dot_label(label)}"];')

    if edges:
        lines.append("")

    for source, target in edges:
        lines.append(f"  issue_{source} -> issue_{target};")

    lines.append("}")
    return "\n".join(lines) + "\n"


def render_graph() -> bool:
    if shutil.which("dot") is None:
        return False

    run_command(["dot", "-Tsvg", str(DOT_PATH), "-o", str(SVG_PATH)])
    run_command(["dot", "-Tpng", str(DOT_PATH), "-o", str(PNG_PATH)])
    return True


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    warn_if_font_missing()
    payload = fetch_issue_data()
    issues = normalize_issues(payload)
    write_issues_json(issues)

    edges = build_edges(issues)
    cycle = find_cycle(edges)
    if cycle:
        cycle_text = " -> ".join(f"#{number}" for number in cycle)
        print(f"Cycle detected: {cycle_text}", file=sys.stderr)
        return 1

    DOT_PATH.write_text(build_dot(issues, edges), encoding="utf-8")

    if render_graph():
        print(f"Generated {ISSUES_JSON_PATH}")
        print(f"Generated {DOT_PATH}")
        print(f"Generated {SVG_PATH}")
        print(f"Generated {PNG_PATH}")
    else:
        print(f"Generated {ISSUES_JSON_PATH}")
        print(f"Generated {DOT_PATH}")
        print("Graphviz 'dot' is not installed; skipped SVG/PNG rendering.")
        print("Install on Ubuntu with: sudo apt-get update && sudo apt-get install -y graphviz")

    print(f"Graph font: {resolve_font_name()} (override with {FONT_ENV_VAR})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
