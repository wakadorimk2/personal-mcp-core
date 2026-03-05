"""Tests for scripts/issue_dag.py."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from issue_dag import (  # noqa: E402
    _escape_label,
    build_edge_list,
    build_edge_list_with_title,
    build_dot,
    build_mmd,
    extract_edges,
    render_png,
)

_ISSUES = [
    {"number": 1, "title": "Base", "body": ""},
    {"number": 2, "title": "Blocked", "body": "blocked by #1"},
    {"number": 3, "title": "Depends", "body": "depends on #1 and requires #2"},
    {"number": 4, "title": "BareRef", "body": "see #3 for context"},
    {"number": 5, "title": "Self", "body": "self ref #5 and external #999"},
]


def test_explicit_blocked_by() -> None:
    assert (2, 1) in extract_edges(_ISSUES)


def test_explicit_depends_on() -> None:
    assert (3, 1) in extract_edges(_ISSUES)


def test_explicit_requires() -> None:
    assert (3, 2) in extract_edges(_ISSUES)


def test_bare_ref() -> None:
    assert (4, 3) in extract_edges(_ISSUES)


def test_self_reference_excluded() -> None:
    edges = extract_edges(_ISSUES)
    assert all(src != dst for src, dst in edges)


def test_external_issue_number_excluded() -> None:
    known = {i["number"] for i in _ISSUES}
    edges = extract_edges(_ISSUES)
    assert all(dst in known for _, dst in edges)


def test_no_edges_emitted_for_body_with_no_refs() -> None:
    edges = extract_edges(_ISSUES)
    assert all(src != 1 for src, _ in edges)


def test_duplicate_edges_excluded() -> None:
    issues = [
        {"number": 1, "title": "A", "body": ""},
        {"number": 2, "title": "B", "body": "blocked by #1 and also see #1"},
    ]
    edges = extract_edges(issues)
    assert len([edge for edge in edges if edge == (2, 1)]) == 1


def test_build_dot_structure() -> None:
    issues = [
        {"number": 1, "title": "Alpha", "body": ""},
        {"number": 2, "title": "Beta", "body": "blocked by #1"},
    ]
    dot = build_dot(issues, extract_edges(issues))
    assert "digraph issues {" in dot
    assert "2 -> 1;" in dot
    assert "#1: Alpha" in dot


def test_build_mmd_structure() -> None:
    issues = [
        {"number": 1, "title": "Alpha", "body": ""},
        {"number": 2, "title": "Beta", "body": "blocked by #1"},
    ]
    mmd = build_mmd(issues, extract_edges(issues))
    assert "flowchart LR" in mmd
    assert "i2 --> i1" in mmd


def test_build_edge_list_structure() -> None:
    edges = {(3, 1), (3, 2), (4, 3)}
    result = build_edge_list(edges)
    assert result.splitlines() == ["#3 -> #1", "#3 -> #2", "#4 -> #3"]


def test_build_edge_list_with_title_structure() -> None:
    issues = [
        {"number": 1, "title": "Alpha", "body": ""},
        {"number": 2, "title": "Beta", "body": ""},
        {"number": 3, "title": "Gamma", "body": ""},
    ]
    edges = {(3, 1), (3, 2)}
    result = build_edge_list_with_title(issues, edges)
    assert result.splitlines() == [
        "#3 (Gamma) -> #1 (Alpha)",
        "#3 (Gamma) -> #2 (Beta)",
    ]


def test_escape_label_double_quote() -> None:
    assert _escape_label('say "hello"') == 'say \\"hello\\"'


def test_escape_label_backslash() -> None:
    assert _escape_label("path\\to\\file") == "path\\\\to\\\\file"


def test_escape_label_backslash_before_quote_no_double_escape() -> None:
    assert _escape_label('\\"') == '\\\\\\"'


def test_build_dot_escapes_title() -> None:
    issues = [{"number": 1, "title": 'Fix "bug" in path\\util', "body": ""}]
    dot = build_dot(issues, set())
    assert '\\"' in dot
    assert "\\\\" in dot


def test_build_mmd_escapes_title() -> None:
    issues = [{"number": 1, "title": 'Fix "bug" in path\\util', "body": ""}]
    mmd = build_mmd(issues, set())
    assert '\\"' in mmd
    assert "\\\\" in mmd


def test_render_png_dot_not_found_exits_1(tmp_path: Path) -> None:
    dot_path = tmp_path / "dag.dot"
    dot_path.write_text("digraph {}")

    with patch("subprocess.run", side_effect=FileNotFoundError):
        with pytest.raises(SystemExit) as exc:
            render_png(dot_path, tmp_path / "dag.png")
    assert exc.value.code == 1


def test_render_png_dot_failure_exits_with_dot_returncode(tmp_path: Path) -> None:
    dot_path = tmp_path / "dag.dot"
    dot_path.write_text("digraph {}")

    mock_result = MagicMock()
    mock_result.returncode = 2
    mock_result.stderr = b"syntax error near line 1"

    with patch("subprocess.run", return_value=mock_result):
        with pytest.raises(SystemExit) as exc:
            render_png(dot_path, tmp_path / "dag.png")
    assert exc.value.code == 2


def test_render_png_success_does_not_raise(tmp_path: Path) -> None:
    dot_path = tmp_path / "dag.dot"
    dot_path.write_text("digraph {}")

    mock_result = MagicMock()
    mock_result.returncode = 0

    with patch("subprocess.run", return_value=mock_result):
        render_png(dot_path, tmp_path / "dag.png")
