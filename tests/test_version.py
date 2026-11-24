import tomllib
from pathlib import Path

from hum2midi import __version__


def test_version_matches_pyproject():
    pyproject = Path(__file__).parent.parent / "pyproject.toml"
    with pyproject.open("rb") as f:
        assert __version__ == tomllib.load(f)["project"]["version"]
