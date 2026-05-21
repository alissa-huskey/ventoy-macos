from contextlib import contextmanager
from io import StringIO
from pathlib import Path

from tests import Stub, copy_fixture
from ventoy_macos.app import App
from ventoy_macos.disk import Disk

bp = breakpoint


def test_app():
    assert App()


def test_app_workdir(tmp_path):
    app = App(Stub(work_dir=str(tmp_path)))

    assert app.workdir == tmp_path


def test_app_workdir_null():
    app = App()

    assert app.workdir.name.startswith("ventoy-macos-")


def test_app_disk():
    app = App(Stub(disk="/dev/disk4"))

    assert isinstance(app.disk, Disk)
    assert app.disk.device == "/dev/disk4"


def test_app_version():
    app = App(Stub(version="1.1.5"))

    assert app.version == "1.1.5"


def test_decompress(tmp_path):
    """
    GIVEN: An extracted ventoy directory
    WHEN: decompress() is called with that directory and a destination path
    THEN: the files boot.img, core.img and ventoy.disk.img should be created
    """

    tmp_ventoy_dir = copy_fixture("ventoy-1.1.12", tmp_path)

    app = App(ventoy_dir=tmp_ventoy_dir, workdir=tmp_path)

    app.decompress()

    assert Path(app.boot_img).is_file()
    assert Path(app.core_img).is_file()
    assert Path(app.disk_img).is_file()


def test_app_download(tmp_path, monkeypatch):
    """
    WHEN: download() is called with a valid ventoy version number and directory
    THEN: the ventoy release for that version should be downloaded to that directory
    """

    def urlretrieve(url, dest):
        """Mock urllib.request.urlretrieve."""
        path = Path(dest)
        path.write_text(url)

    with monkeypatch.context() as m:
        m.setattr("urllib.request.urlretrieve", urlretrieve)

        version = "1.1.11"
        name = f"ventoy-{version}-linux.tar.gz"
        url = f"https://github.com/ventoy/Ventoy/releases/download/v{version}/{name}"
        dest = tmp_path / name

        app = App(version=version, workdir=tmp_path)
        app.download()

        tarball = Path(app.tarball)

        assert app.tarball == str(dest)
        assert tarball.is_file() and tarball.read_text() == url


def test_app_extract(tmp_path):
    """
    WHEN: extract() is called with the path to a tarball and a destination path
    THEN: it should extract the tarball to that destination directory
    """
    tmp_tarball = copy_fixture("ventoy-1.1.12.tar.gz", tmp_path)
    path = tmp_path / "ventoy-1.1.12"

    app = App(tarball=tmp_tarball, workdir=str(tmp_path))
    app.extract()

    assert app.ventoy_dir == str(path)
    assert path.is_dir()


def test_app_get_latest(monkeypatch):
    """
    WHEN: get_latest() is called
    THEN: it should return the latest ventoy release version.
    """
    @contextmanager
    def urlopen(*args, **kwargs):
        """Mock urlopen."""
        yield StringIO('{"tag_name": "v1.1.12"}')

    with monkeypatch.context() as m:
        m.setattr("urllib.request.urlopen", urlopen)

        app = App()
        tag = app.get_latest()

        assert tag == "1.1.12"


#  def test_app_():
#      ...
