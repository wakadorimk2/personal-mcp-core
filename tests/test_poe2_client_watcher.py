from personal_mcp.tools.poe2_client_watcher import parse_area_line


def test_parse_area_line_returns_area_name() -> None:
    line = "2024/03/15 12:34:56 1234567 ab [SCENE] Set Source [Crimson Temple]"
    assert parse_area_line(line) == "Crimson Temple"


def test_parse_area_line_returns_none_for_unrelated_line() -> None:
    line = "2024/03/15 12:34:56 1234567 ab [INFO] some other log line"
    assert parse_area_line(line) is None


def test_parse_area_line_empty_string() -> None:
    assert parse_area_line("") is None


def test_parse_area_line_minimal_match() -> None:
    assert parse_area_line("[SCENE] Set Source [Hideout]") == "Hideout"


def test_parse_area_line_area_with_spaces() -> None:
    line = "[SCENE] Set Source [The Twilight Strand]"
    assert parse_area_line(line) == "The Twilight Strand"


def test_parse_area_line_null_is_skipped() -> None:
    line = "2026/03/03 21:39:37 243052531 7fbd122e [INFO Client 20632] [SCENE] Set Source [(null)]"
    assert parse_area_line(line) is None


def test_parse_area_line_unknown_is_skipped() -> None:
    line = "2026/03/03 21:39:17 243033031 7fbd122e [INFO Client 20632] [SCENE] Set Source [(unknown)]"
    assert parse_area_line(line) is None
