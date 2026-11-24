import re
from pathlib import Path

from hum2midi import __version__


def test_version_matches_pyproject():
    pyproject = (Path(__file__).parent.parent / "pyproject.toml").read_text()
    match = re.search(r'^version = "(.*)"', pyproject, re.MULTILINE)
    assert __version__ == match[1]
