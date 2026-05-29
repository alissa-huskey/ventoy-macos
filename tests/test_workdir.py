import json
from pathlib import Path

import pytest

from tests import Stub, copy_fixture, return_false, return_true
from ventoy_macos import VentoyMacosError
from ventoy_macos.disk_image import DiskImage
from ventoy_macos.workdir import Workdir

bp = breakpoint


@pytest.fixture
def workdir(tmp_path) -> Workdir:
    """Return a Workdir object."""
    return Workdir(tmp_path, version="1.1.12")


@pytest.fixture
def version_path(tmp_path):
    """."""
    return tmp_path / "1.1.12"


def test_workdir():
    assert Workdir()


def test_workdir_tarball_path(workdir, version_path):
    assert workdir.tarball_path == version_path / "ventoy-1.1.12-linux.tar.gz"


def test_workdir_ventoy_dir(workdir, version_path):
    assert workdir.ventoy_dir == version_path / "ventoy-1.1.12"


def test_workdir_find_ventoy_dir(monkeypatch, workdir, version_path):
    ventoy_dir = version_path / "ventoy-1.1.12"
    ventoy_dir.mkdir(parents=True)

    path = version_path / "ventoy-1.1.12"

    assert workdir.find_ventoy_dir("1.1.12") == path
    assert workdir.find_ventoy_dir() == path
    assert workdir.find_ventoy_dir("1.1.11") is False


def test_workdir_request(monkeypatch, workdir):
    with monkeypatch.context() as m:
        expected = Stub(ok=True, status_code="200", reason="OK")
        m.setattr("requests.get", lambda *a, **k: expected)

        response = workdir.request("https://jsonplaceholder.typicode.com/posts")

        assert response and response == expected


def test_workdir_request_failed(monkeypatch, workdir):
    with monkeypatch.context() as m:
        response = Stub(ok=False, status_code="400", reason="NOT FOUND")

        m.setattr("requests.get", lambda url, *a, **k: response)

        with pytest.raises(VentoyMacosError) as e:
            workdir.request("https://jsonplaceholder.typicode.com/posts")

        exception = e.value

        message = (
            "Request Failed [400 NOT FOUND]: "
            "https://jsonplaceholder.typicode.com/posts"
        )

        assert str(exception) == message
        assert exception.response and exception.response == response


def test_workdir_get_latest(monkeypatch):
    """
    WHEN: .get_latest() is called
    THEN: it should return the latest ventoy release version.
    """
    with monkeypatch.context() as m:
        response = Stub(ok=True, json=lambda: json.loads('{"tag_name": "v1.1.12"}'))
        m.setattr("requests.get", lambda url, *a, **k: response)

        tag = Workdir.get_latest()

        assert tag == "1.1.12"


def test_workdir_download(tmp_path, monkeypatch, workdir):
    """
    WHEN: .download() is called with a valid ventoy version number and directory
    THEN: the ventoy release for that version should be downloaded to that directory
    """

    with monkeypatch.context() as m:
        expected = Stub(content=b'file contents', ok=True)
        m.setattr("requests.get", lambda url, *a, **k: expected)
        workdir.mkdirs()

        response = workdir.download()

        path = workdir.tarball_path

        assert response == expected
        assert path.is_file() and path.read_bytes() == b"file contents"


def test_workdir_extract(monkeypatch, workdir, version_path):
    """
    WHEN: .extract() is called with the path to a tarball and a destination path
    THEN: it should extract the tarball to that destination directory
    """
    workdir.mkdirs()
    copy_fixture("ventoy-1.1.12-linux.tar.gz", version_path)

    workdir.extract()

    assert workdir.ventoy_dir.is_dir()


def test_workdir_decompress(tmp_path, version_path, shared_datadir):
    image = DiskImage(
        source=shared_datadir / "ventoy-1.1.12" / "boot" / "core.img.xz",
        dest=version_path / "core.img",
    )

    workdir = Workdir(
        tmp_path,
        version="1.1.12",
        images={"core_img": image},
    )
    workdir.mkdirs()
    workdir.decompress()

    assert image.dest.path.is_file()


def test_workdir_images(shared_datadir):
    workdir = Workdir(Path("/tmp"), version="1.1.12")

    assert len(workdir.images) == 3
    assert all([isinstance(img, DiskImage) for img in workdir.images.values()])


def test_workdir_has_images():
    workdir = Workdir(
        images={
            "core_img": Stub(dest=Stub(exists=return_true)),
            "disk_img": Stub(dest=Stub(exists=return_false)),
        },
    )

    assert workdir.has_images() is False


def test_workdir_chmod(tmp_path, version_path):
    """
    drwxr-xr-x 18 alissa staff 576  Apr 23 04:04 ventoy-1.1.12
    -rw-r--r--  1 alissa staff 2.6K Apr 23 04:04 ventoy-1.1.12/README
    -rwxr-xr-x  1 alissa staff 2.4K Apr 23 04:04 ventoy-1.1.12/Ventoy2Disk.sh
    """

    version_path.mkdir(parents=True)
    copy_fixture("ventoy-1.1.12-linux.tar.gz", version_path)

    # relpath -> (old permission, new permission)
    # a small sample of files in the extracted dir
    # (old permission is just for reference)
    files = {
        "ventoy-1.1.12": (0o40755, 0o40777),
        "ventoy-1.1.12/README": (0o100644, 0o100666),
        "ventoy-1.1.12/Ventoy2Disk.sh": (0o100755, 0o100777),
    }

    workdir = Workdir(tmp_path, version="1.1.12")
    workdir.mkdirs()

    workdir.extract()

    workdir.chmod()

    for name, (old, new) in files.items():
        path = version_path / name
        mode = path.stat().st_mode
        _mode = oct(mode)

        assert mode == new, f"{name}: Expected mode: {new:#o} but got {_mode}"


def test_workdir_base():
    path = "/tmp/ventoy-macos-xxx"
    workdir = Workdir(path)
    assert workdir.base == Path(path)


def test_workdir_path():
    path = "/tmp/ventoy-macos-xxx"
    workdir = Workdir(path, version="1.1.12")
    assert workdir.path == Path(path) / "1.1.12"


def test_workdir_mktemp(monkeypatch, tmp_path, version_path):
    """
    GIVEN: A Workdir object with no .base Path set
    WHEN: .mktemp() is called
    THEN: .path should be set to a directory created by tempfile.mkdtemp()
    AND: the name of the dir should start with ventoy-macos-
    """
    with monkeypatch.context() as m:
        m.setattr(Workdir, "TMPDIR", tmp_path)

        workdir = Workdir()

        workdir.mktemp()

        assert isinstance(workdir.base, Path)

        assert workdir.base.name.startswith("ventoy-macos")
        assert workdir.base.is_dir()


def test_workdir_mkdirs_from_tmpdir(monkeypatch, tmp_path):
    """
    GIVEN: A Workdir object with no .path set
    WHEN: .mkdirs() is called
    THEN: .path should be set to a directory created by tempfile.mkdtemp()
    AND: the name of the dir should start with ventoy-macos-
    AND: the subdirectory data/ should be created
    """
    with monkeypatch.context() as m:
        m.setattr(Workdir, "TMPDIR", tmp_path)

        workdir = Workdir(version="1.1.12")

        workdir.mkdirs()

        assert isinstance(workdir.base, Path)
        assert isinstance(workdir.path, Path)

        assert workdir.base.name.startswith("ventoy-macos")
        assert workdir.base.is_dir()
        assert workdir.path.name == "1.1.12"
        assert workdir.path.is_dir()
        assert (workdir.path / "data").is_dir()


def test_workdir_mkdirs_from_path(tmp_path):
    """
    GIVEN: A Workdir object with a .path set
    WHEN: .mkdirs() is called
    AND: the subdirectory data/ should be created
    """
    workdir = Workdir(tmp_path, version="1.1.12")

    workdir.mkdirs()

    assert Workdir.TMPDIR is None, "Sanity check"
    assert workdir.base == tmp_path
    assert workdir.base.is_dir()
    assert workdir.path.name == "1.1.12"
    assert workdir.path.is_dir()
    assert (workdir.path / "data").is_dir()


def test_workdir_str():
    workdir = Workdir(Path("/tmp/ventoy-macos-xxx"), version="1.1.12")

    assert str(workdir) == "/tmp/ventoy-macos-xxx/1.1.12"


def test_workdir_base_is_path(tmp_path, version_path):
    workdir = Workdir()
    workdir.base = version_path

    assert workdir.base == tmp_path
    assert workdir.path == version_path
    assert workdir.version == "1.1.12"


#  @pytest.mark.skip
#  def test_workdir_():
#      ...
