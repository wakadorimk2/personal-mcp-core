from __future__ import annotations

import io
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Tuple

import pytest

from personal_mcp.tools import candidates as candidates_mod
from personal_mcp.core.event import build_v1_record
from personal_mcp.storage.sqlite import append_sqlite
from personal_mcp.tools.candidates import (
    FIXED_CANDIDATES,
    MAX_CANDIDATE_LENGTH,
    _extract_candidate_text,
    _extract_candidate_texts,
    _shorten_text,
    list_candidates,
)


def _ts(days_ago: int, seq: int) -> str:
    base = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return (base.replace(microsecond=0) + timedelta(seconds=seq)).isoformat()


def _add_event(
    db_path: Path,
    *,
    text: str,
    days_ago: int = 0,
    seq: int = 0,
    domain: str = "general",
    kind: str = "note",
) -> None:
    record = build_v1_record(
        ts=_ts(days_ago, seq),
        domain=domain,
        text=text,
        tags=[],
        kind=kind,
        source="test",
    )
    append_sqlite(db_path, record)


def _norm(text: str) -> str:
    return text.strip().lower()


def _sources(items: List[Dict[str, str]]) -> List[str]:
    return [x["source"] for x in items]


def _make_handler_for_test(data_dir: str):
    from personal_mcp.adapters.http_server import _make_handler

    return _make_handler(data_dir)


def _new_handler(handler_cls, path: str):
    handler = handler_cls.__new__(handler_cls)
    handler.headers = {}
    handler.rfile = io.BytesIO(b"")
    handler.wfile = io.BytesIO()
    handler.path = path
    handler.request_version = "HTTP/1.1"
    return handler


def _do_get_json(handler_cls, path: str) -> List[Tuple[int, Any]]:
    handler = _new_handler(handler_cls, path)
    responses: List[Tuple[int, Any]] = []
    handler._json = lambda status, body: responses.append((status, body))
    handler.do_GET()
    return responses


def test_list_candidates_cold_start_returns_fixed_only(data_dir: Path) -> None:
    db_path = data_dir / "events.db"
    for i in range(6):
        _add_event(db_path, text=f"event-{i}", seq=i)

    got = list_candidates(data_dir=str(data_dir))
    expected = [{"text": t, "source": "fixed"} for t in FIXED_CANDIDATES]
    assert got == expected


@pytest.mark.parametrize("count", [7, 8])
def test_list_candidates_threshold_7_and_8_enable_non_fixed_sources(
    data_dir: Path, count: int
) -> None:
    db_path = data_dir / "events.db"
    for i in range(count):
        _add_event(db_path, text=f"log-{i}", seq=i)

    got = list_candidates(data_dir=str(data_dir))
    assert any(item["source"] != "fixed" for item in got)


def test_list_candidates_dedup_prefers_higher_priority_source(data_dir: Path) -> None:
    db_path = data_dir / "events.db"
    texts = ["alpha", "beta", "gamma", "delta", "epsilon", "zeta", "  休憩  "]
    for i, text in enumerate(texts):
        _add_event(db_path, text=text, seq=i)

    got = list_candidates(data_dir=str(data_dir))
    rest_items = [item for item in got if _norm(item["text"]) == "休憩"]
    assert len(rest_items) == 1
    assert rest_items[0]["source"] == "recent"


def test_list_candidates_can_include_today_frequent_source(data_dir: Path) -> None:
    db_path = data_dir / "events.db"
    _add_event(db_path, text="today-only", seq=1)
    _add_event(db_path, text="today-only", seq=2)
    for i in range(3, 13):
        _add_event(db_path, text="recent-repeat", seq=i)

    got = list_candidates(data_dir=str(data_dir))
    today_only = [item for item in got if item["text"] == "today-only"]
    assert len(today_only) == 1
    assert today_only[0]["source"] == "today_frequent"


def test_list_candidates_can_include_7d_frequent_source(data_dir: Path) -> None:
    db_path = data_dir / "events.db"
    _add_event(db_path, text="week-only", days_ago=2, seq=1)
    _add_event(db_path, text="week-only", days_ago=2, seq=2)
    for i in range(3, 14):
        _add_event(db_path, text="today-repeat", seq=i)

    got = list_candidates(data_dir=str(data_dir))
    week_only = [item for item in got if item["text"] == "week-only"]
    assert len(week_only) == 1
    assert week_only[0]["source"] == "7d_frequent"


def test_list_candidates_caps_at_8(data_dir: Path) -> None:
    db_path = data_dir / "events.db"
    for i in range(20):
        _add_event(db_path, text=f"event-{i:02d}", seq=i)

    got = list_candidates(data_dir=str(data_dir))
    assert len(got) == 8
    assert _sources(got) == ["recent"] * 8


def test_http_get_candidates_200(data_dir: Path) -> None:
    db_path = data_dir / "events.db"
    for i in range(8):
        _add_event(db_path, text=f"event-{i}", seq=i)

    handler_cls = _make_handler_for_test(str(data_dir))
    responses = _do_get_json(handler_cls, "/api/candidates")
    assert len(responses) == 1
    status, body = responses[0]
    assert status == 200
    assert isinstance(body, list)
    assert len(body) <= 8
    assert all("text" in item and "source" in item for item in body)


# --- _shorten_text unit tests ---


def test_shorten_text_short_text_unchanged() -> None:
    assert _shorten_text("作業開始") == "作業開始"
    assert _shorten_text("休憩") == "休憩"
    assert _shorten_text("") == ""


def test_shorten_text_at_boundary_unchanged() -> None:
    text = "a" * MAX_CANDIDATE_LENGTH
    assert _shorten_text(text) == text


def test_shorten_text_long_text_within_limit() -> None:
    long_text = "あいうえおかきくけこさしすせそ"  # 15 chars
    result = _shorten_text(long_text)
    assert len(result) <= MAX_CANDIDATE_LENGTH


def test_shorten_text_splits_on_japanese_delimiter() -> None:
    assert _shorten_text("作業開始：朝のタスク確認") == "作業開始"
    assert _shorten_text("コーディング 詳細な説明が続く") == "コーディング"
    assert _shorten_text("移動。買い物をした") == "移動"


def test_shorten_text_splits_on_arrow() -> None:
    result = _shorten_text("作業開始→タスク管理の確認")
    assert result == "作業開始"
    assert len(result) <= MAX_CANDIDATE_LENGTH


# --- integration: long-text events produce short candidates ---


def test_list_candidates_long_events_produce_short_candidates(data_dir: Path) -> None:
    db_path = data_dir / "events.db"
    long_texts = [
        "今日の作業をしっかりと開始しました",
        "昼休みの後に作業を再開した記録",
        "移動中にメモしておく内容です",
        "コードレビューを実施しました",
        "夕方の振り返りをしています",
        "明日のタスクを整理した",
        "会議の準備をしていた",
        "設計について検討した",
        "ドキュメントを更新しました",
        "テストを書いていた",
    ]
    for i, text in enumerate(long_texts):
        _add_event(db_path, text=text, seq=i)

    got = list_candidates(data_dir=str(data_dir))
    non_fixed = [item for item in got if item["source"] != "fixed"]

    assert non_fixed, "long-text events should produce at least one non-fixed candidate"
    assert all(len(item["text"]) <= MAX_CANDIDATE_LENGTH for item in non_fixed), (
        f"all non-fixed candidates must be <= {MAX_CANDIDATE_LENGTH} chars: {non_fixed}"
    )


class _FakeWord:
    def __init__(self, surface: str, pos1: str, pos2: str = "") -> None:
        self.surface = surface
        self.feature = SimpleNamespace(pos1=pos1, pos2=pos2, lemma=surface)


class _FakeTagger:
    def __init__(self, mapping: Dict[str, List[_FakeWord]]) -> None:
        self._mapping = mapping

    def __call__(self, text: str) -> List[_FakeWord]:
        return list(self._mapping[text])


def _legacy_feature_attr(word: Any, name: str) -> str:
    feature = getattr(word, "feature", None)
    value = getattr(feature, name, "")
    if value in (None, "*"):
        return ""
    return str(value)


def _legacy_tokenized_candidate(text: str) -> tuple[str, bool]:
    tagger = candidates_mod._get_tagger()
    if tagger is None:
        return "", False

    words = list(tagger(text))
    chunks: List[str] = []
    current: List[str] = []
    sensitive_hit = False

    for idx, word in enumerate(words):
        surface = str(getattr(word, "surface", "")).strip()
        if not surface:
            continue

        pos1 = _legacy_feature_attr(word, "pos1")
        pos2 = _legacy_feature_attr(word, "pos2")
        next_surface = ""
        if idx + 1 < len(words):
            next_surface = str(getattr(words[idx + 1], "surface", "")).strip()

        if next_surface in candidates_mod._HONORIFICS and pos1 == "名詞":
            sensitive_hit = True
            if current:
                chunks.append("".join(current))
                current = []
            continue

        if (
            pos1 == "名詞"
            and pos2 in {"普通名詞", "固有名詞"}
            and surface not in candidates_mod._HONORIFICS
        ):
            current.append(surface)
            continue

        if current:
            chunks.append("".join(current))
            current = []

    if current:
        chunks.append("".join(current))

    for chunk in chunks:
        candidate = candidates_mod._clean_candidate_text(chunk)
        if candidates_mod._is_sensitive_label(candidate):
            sensitive_hit = True
            continue
        if candidates_mod._is_meaningful_candidate(candidate):
            return candidate, sensitive_hit

    if sensitive_hit:
        return "", True
    return "", False


def _legacy_extract_candidate_text(text: str) -> str:
    if candidates_mod._ASCII_SLUG.fullmatch(text.strip()):
        return candidates_mod._clean_candidate_text(text)

    tokenized, sensitive_hit = _legacy_tokenized_candidate(text)
    if tokenized:
        return tokenized
    if sensitive_hit:
        return ""

    fallback = candidates_mod._clean_candidate_text(candidates_mod._shorten_text(text))
    if candidates_mod._is_sensitive_label(fallback):
        return ""
    if candidates_mod._is_meaningful_candidate(fallback):
        return fallback
    return ""


def test_extract_candidate_text_prefers_tokenized_noun_chunk(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mapping = {
        "Codexを爆速で消費している": [
            _FakeWord("Codex", "名詞", "普通名詞"),
            _FakeWord("を", "助詞", "格助詞"),
            _FakeWord("爆", "記号", "一般"),
            _FakeWord("速", "名詞", "普通名詞"),
            _FakeWord("で", "助詞", "格助詞"),
            _FakeWord("消費", "名詞", "普通名詞"),
        ],
        "コードレビューを実施しました": [
            _FakeWord("コード", "名詞", "普通名詞"),
            _FakeWord("レビュー", "名詞", "普通名詞"),
            _FakeWord("を", "助詞", "格助詞"),
            _FakeWord("実施", "名詞", "普通名詞"),
        ],
    }
    monkeypatch.setattr(candidates_mod, "_get_tagger", lambda: _FakeTagger(mapping))

    assert _extract_candidate_text("Codexを爆速で消費している") == "Codex"
    assert _extract_candidate_text("コードレビューを実施しました") == "コードレビュー"


def test_extract_candidate_texts_returns_multiple_candidates_in_natural_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mapping = {
        "CodexとClaude Codeでレビューした": [
            _FakeWord("Codex", "名詞", "普通名詞"),
            _FakeWord("と", "助詞", "格助詞"),
            _FakeWord("Claude", "名詞", "普通名詞"),
            _FakeWord("Code", "名詞", "普通名詞"),
            _FakeWord("で", "助詞", "格助詞"),
            _FakeWord("レビュー", "名詞", "普通名詞"),
        ],
        "設計レビューと実装を進めた": [
            _FakeWord("設計", "名詞", "普通名詞"),
            _FakeWord("レビュー", "名詞", "普通名詞"),
            _FakeWord("と", "助詞", "格助詞"),
            _FakeWord("実装", "名詞", "普通名詞"),
            _FakeWord("を", "助詞", "格助詞"),
            _FakeWord("進め", "動詞", "一般"),
        ],
    }
    monkeypatch.setattr(candidates_mod, "_get_tagger", lambda: _FakeTagger(mapping))

    assert _extract_candidate_texts("CodexとClaude Codeでレビューした") == [
        "Codex",
        "Claude",
    ]
    assert _extract_candidate_texts("設計レビューと実装を進めた") == [
        "設計レビュー",
        "実装",
    ]


def test_extract_candidate_text_skips_name_with_honorific(monkeypatch: pytest.MonkeyPatch) -> None:
    mapping = {
        "久しぶりに沙耶ちゃんに会う": [
            _FakeWord("久し", "形容詞", "一般"),
            _FakeWord("沙耶", "名詞", "固有名詞"),
            _FakeWord("ちゃん", "接尾辞", "名詞的"),
            _FakeWord("会う", "動詞", "一般"),
        ]
    }
    monkeypatch.setattr(candidates_mod, "_get_tagger", lambda: _FakeTagger(mapping))

    assert _extract_candidate_text("久しぶりに沙耶ちゃんに会う") == ""


def test_extract_candidate_texts_keep_safe_candidate_after_sensitive_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mapping = {
        "山田さんと1on1した": [
            _FakeWord("山田", "名詞", "固有名詞"),
            _FakeWord("さん", "接尾辞", "名詞的"),
            _FakeWord("と", "助詞", "格助詞"),
            _FakeWord("1", "名詞", "数詞"),
            _FakeWord("on", "名詞", "普通名詞"),
            _FakeWord("1", "名詞", "数詞"),
            _FakeWord("し", "動詞", "非自立可能"),
        ]
    }
    monkeypatch.setattr(candidates_mod, "_get_tagger", lambda: _FakeTagger(mapping))

    assert _extract_candidate_texts("山田さんと1on1した") == ["1on1"]


def test_extract_candidate_text_fallback_skips_sensitive_label(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(candidates_mod, "_get_tagger", lambda: None)

    assert _extract_candidate_text("沙耶ちゃん") == ""


def test_list_candidates_filters_sensitive_name_when_tagger_available(
    data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mapping = {
        "久しぶりに沙耶ちゃんに会う": [
            _FakeWord("久し", "形容詞", "一般"),
            _FakeWord("沙耶", "名詞", "固有名詞"),
            _FakeWord("ちゃん", "接尾辞", "名詞的"),
            _FakeWord("会う", "動詞", "一般"),
        ],
        "Codexを爆速で消費している": [
            _FakeWord("Codex", "名詞", "普通名詞"),
            _FakeWord("を", "助詞", "格助詞"),
            _FakeWord("消費", "名詞", "普通名詞"),
        ],
        "コードレビューを実施しました": [
            _FakeWord("コード", "名詞", "普通名詞"),
            _FakeWord("レビュー", "名詞", "普通名詞"),
            _FakeWord("を", "助詞", "格助詞"),
            _FakeWord("実施", "名詞", "普通名詞"),
        ],
    }
    monkeypatch.setattr(candidates_mod, "_get_tagger", lambda: _FakeTagger(mapping))

    db_path = data_dir / "events.db"
    texts = [
        "久しぶりに沙耶ちゃんに会う",
        "Codexを爆速で消費している",
        "コードレビューを実施しました",
        "移動",
        "休憩",
        "振り返り",
        "テストを書いていた",
    ]
    for i, text in enumerate(texts):
        _add_event(db_path, text=text, seq=i)

    got = list_candidates(data_dir=str(data_dir))
    labels = [item["text"] for item in got]

    assert "Codex" in labels
    assert "コードレビュー" in labels
    assert all("沙耶" not in label for label in labels)


def test_list_candidates_caps_at_8_even_when_text_yields_multiple_candidates(
    data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mapping = {
        "CodexとClaude Codeでレビューした": [
            _FakeWord("Codex", "名詞", "普通名詞"),
            _FakeWord("と", "助詞", "格助詞"),
            _FakeWord("Claude", "名詞", "普通名詞"),
            _FakeWord("Code", "名詞", "普通名詞"),
            _FakeWord("で", "助詞", "格助詞"),
            _FakeWord("レビュー", "名詞", "普通名詞"),
        ],
        "設計レビューと実装を進めた": [
            _FakeWord("設計", "名詞", "普通名詞"),
            _FakeWord("レビュー", "名詞", "普通名詞"),
            _FakeWord("と", "助詞", "格助詞"),
            _FakeWord("実装", "名詞", "普通名詞"),
            _FakeWord("を", "助詞", "格助詞"),
            _FakeWord("進め", "動詞", "一般"),
        ],
        "GitHub issue triageとコードレビューを進めた": [
            _FakeWord("GitHub", "名詞", "普通名詞"),
            _FakeWord("issue", "名詞", "普通名詞"),
            _FakeWord("triage", "名詞", "普通名詞"),
            _FakeWord("と", "助詞", "格助詞"),
            _FakeWord("コード", "名詞", "普通名詞"),
            _FakeWord("レビュー", "名詞", "普通名詞"),
        ],
        "VS CodeとCodexで調査した": [
            _FakeWord("VS", "名詞", "普通名詞"),
            _FakeWord("Code", "名詞", "普通名詞"),
            _FakeWord("と", "助詞", "格助詞"),
            _FakeWord("Codex", "名詞", "普通名詞"),
            _FakeWord("で", "助詞", "格助詞"),
            _FakeWord("調査", "名詞", "普通名詞"),
        ],
        "1on1と振り返りを進めた": [
            _FakeWord("1", "名詞", "数詞"),
            _FakeWord("on", "名詞", "普通名詞"),
            _FakeWord("1", "名詞", "数詞"),
            _FakeWord("と", "助詞", "格助詞"),
            _FakeWord("振り返り", "名詞", "普通名詞"),
            _FakeWord("を", "助詞", "格助詞"),
            _FakeWord("進め", "動詞", "一般"),
        ],
    }
    monkeypatch.setattr(candidates_mod, "_get_tagger", lambda: _FakeTagger(mapping))

    db_path = data_dir / "events.db"
    texts = [
        "CodexとClaude Codeでレビューした",
        "設計レビューと実装を進めた",
        "GitHub issue triageとコードレビューを進めた",
        "VS CodeとCodexで調査した",
        "1on1と振り返りを進めた",
        "移動",
        "休憩",
    ]
    for i, text in enumerate(texts):
        _add_event(db_path, text=text, seq=i)

    got = list_candidates(data_dir=str(data_dir))
    assert len(got) == 8
    assert _sources(got) == ["recent"] * 8
    # recent source is consumed in newest-first order, and each text can emit up to
    # two candidates. In this fixture those eight slots fill with:
    # 休憩, 移動, 1on1, 振り返り, VS Code, Codex, GitHub, コードレビュー.
    # GitHub stays because the tokenizer tries shorter noun chunks once
    # "GitHub issue triage" exceeds MAX_CANDIDATE_LENGTH.
    assert [item["text"] for item in got] == [
        "休憩",
        "移動",
        "1on1",
        "振り返り",
        "VS Code",
        "Codex",
        "GitHub",
        "コードレビュー",
    ]


@pytest.mark.skipif(candidates_mod.Tagger is None, reason="fugashi not installed")
@pytest.mark.parametrize(
    ("text", "legacy", "current"),
    [
        ("Codexを爆速で消費している", "Codex", "Codex"),
        ("コードレビューを実施しました", "コードレビュー", "コードレビュー"),
        ("GitHub issue triageを進めた", "GitHubissu", "GitHub"),
        ("VS Codeで調査した", "VSCode", "VS Code"),
        ("山田さんと1on1した", "", "1on1"),
        ("朝から開発環境を立ち上げ直した", "開発環境", "開発環境"),
    ],
)
def test_extract_candidate_text_real_tagger_comparison_samples(
    text: str, legacy: str, current: str
) -> None:
    assert _legacy_extract_candidate_text(text) == legacy
    assert _extract_candidate_text(text) == current


@pytest.mark.skipif(candidates_mod.Tagger is None, reason="fugashi not installed")
@pytest.mark.parametrize(
    ("text", "legacy", "current"),
    [
        ("CodexとClaude Codeでレビューした", "Codex", ["Codex", "Claude"]),
        ("設計レビューと実装を進めた", "設計レビュー", ["設計レビュー", "実装"]),
        ("山田さんと1on1した", "", ["1on1"]),
        (
            "GitHub issue triageとコードレビューを進めた",
            "GitHubissu",
            ["GitHub", "コードレビュー"],
        ),
        ("VS CodeとCodexで調査した", "VSCode", ["VS Code", "Codex"]),
    ],
)
def test_extract_candidate_texts_real_tagger_comparison_samples(
    text: str, legacy: str, current: List[str]
) -> None:
    assert _legacy_extract_candidate_text(text) == legacy
    assert _extract_candidate_texts(text) == current


@pytest.mark.skipif(candidates_mod.Tagger is None, reason="fugashi not installed")
def test_list_candidates_real_tagger_keeps_natural_candidates(data_dir: Path) -> None:
    db_path = data_dir / "events.db"
    texts = [
        "GitHub issue triageを進めた",
        "VS Codeで調査した",
        "山田さんと1on1した",
        "コードレビューを実施しました",
        "Codexを爆速で消費している",
        "朝から開発環境を立ち上げ直した",
        "休憩",
    ]
    for i, text in enumerate(texts):
        _add_event(db_path, text=text, seq=i)

    got = list_candidates(data_dir=str(data_dir))
    labels = [item["text"] for item in got]

    assert "GitHub" in labels
    assert "VS Code" in labels
    assert "1on1" in labels
    assert "コードレビュー" in labels
    assert "消費" not in labels
    assert "実施" not in labels
    assert "調査" not in labels
    assert all("山田" not in label for label in labels)
