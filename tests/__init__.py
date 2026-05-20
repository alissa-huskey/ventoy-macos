from pathlib import Path
from shutil import copy, copytree


def copy_fixture(name: str, dest: Path) -> Path:
    """Copy fixtures.

    Arguments:
        name (str): name of file or directory to copy
        dest (Path): path to destination directory

    Returns:
        Path to copied file or directory
    """
    fixtures = Path(__file__).parent / "fixtures"
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
