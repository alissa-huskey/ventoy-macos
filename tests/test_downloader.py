from contextlib import contextmanager
from io import StringIO
from pathlib import Path
from shutil import copy, copytree

from ventoy_macos.downloader import decompress, download, extract, get_latest

bp = breakpoint


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


def test_decompress(tmp_path):
    """
    GIVEN: An extracted ventoy directory
    WHEN: decompress() is called with that directory and a destination path
    THEN: the files boot.img, core.img and ventoy.disk.img should be created
    """
    tmp_ventoy_dir = copy_fixture("ventoy-1.1.12", tmp_path)

    images = decompress(tmp_ventoy_dir, tmp_path)

    assert len(images) == 3
    assert Path(images[0]).is_file()
    assert Path(images[1]).is_file()
    assert Path(images[2]).is_file()


def test_download(tmp_path, monkeypatch):
    """
    WHEN: download() is called with a valid ventoy version number and directory
    THEN: the ventoy release for that version should be downloaded to that directory
    """

    def urlretrieve(url, dest):
        """Mock urllib.request.urlretrieve."""
        path = Path(dest)
        path.write_text(url)

    monkeypatch.setattr("urllib.request.urlretrieve", urlretrieve)

    version = "1.1.11"
    name = f"ventoy-{version}-linux.tar.gz"
    url = f"https://github.com/ventoy/Ventoy/releases/download/v{version}/{name}"
    dest = tmp_path / name
    result = download(version, str(tmp_path))

    assert result == str(dest)
    assert dest.is_file() and dest.read_text() == url


def test_extract(tmp_path):
    """
    WHEN: extract() is called with the path to a tarball and a destination path
    THEN: it should extract the tarball to that destination directory
    """
    tmp_tarball = copy_fixture("ventoy-1.1.12.tar.gz", tmp_path)
    path = tmp_path / "ventoy-1.1.12"

    extracted = extract(str(tmp_tarball), str(tmp_path))

    assert extracted == str(path)
    assert path.is_dir()


def test_get_latest(monkeypatch):
    """
    WHEN: get_latest() is called
    THEN: it should return the latest ventoy release version.
    """
    @contextmanager
    def urlopen(*args, **kwargs):
        """Mock urlopen."""
        yield StringIO('{"tag_name": "v1.1.12"}')

    monkeypatch.setattr("urllib.request.urlopen", urlopen)

    tag = get_latest()

    assert tag == "1.1.12"


#  def test_():
#      """
#      GIVEN: ...
#      WHEN: ...
#      THEN: ...
#      """
