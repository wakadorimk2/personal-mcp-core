import pytest
from pathlib import Path


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    """本番 data/ を汚染しない一時ディレクトリ"""
    d = tmp_path / "data"
    d.mkdir()
    return d
