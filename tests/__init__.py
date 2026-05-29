"""Ventoy for macOS."""
from pathlib import Path
from shutil import copy, copytree

from ventoy_macos.object import Object

COMMANDS = []


def noop(*a, **k):
    """Do nothing."""


def mock_run(args, **kwargs):
    """Mock run command."""
    COMMANDS.append(args)
    return Stub(returncode=0)


class Stub(Object):
    """Easily stub objects."""

    def __getattr__(self, name: str):
        """Return None for missing attributes."""
        return None


def copy_fixture(name: str, dest: Path) -> Path:
    """Copy fixtures.

    Arguments:
        name (str): name of file or directory to copy
        dest (Path): path to destination directory

    Returns:
        Path to copied file or directory
    """
    fixtures = Path(__file__).parent / "data"
    source = fixtures / name
    path = dest / name

    if source.is_dir():
        copier = copytree
    elif source.is_file():
        copier = copy
    else:
        raise Exception(f"Not a valid fixture: {source}")

    copier(source, path)

    return path
