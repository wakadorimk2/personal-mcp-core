import os
import sys
from pathlib import Path

import pytest


_SRC_DIR = Path(__file__).resolve().parents[1] / "src"
_SRC_DIR_STR = str(_SRC_DIR)
if _SRC_DIR_STR not in sys.path:
    sys.path.insert(0, _SRC_DIR_STR)

_existing_pythonpath = os.environ.get("PYTHONPATH", "")
_pythonpath_entries = [entry for entry in _existing_pythonpath.split(os.pathsep) if entry]
if _SRC_DIR_STR not in _pythonpath_entries:
    os.environ["PYTHONPATH"] = os.pathsep.join([_SRC_DIR_STR, *_pythonpath_entries])


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    """本番 data/ を汚染しない一時ディレクトリ"""
    d = tmp_path / "data"
    d.mkdir()
    return d
