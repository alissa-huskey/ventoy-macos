from pathlib import Path

from tests import Stub, copy_fixture
from ventoy_macos.app import App
from ventoy_macos.disk import Disk
from ventoy_macos.disk_image import DiskImage

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
    assert app.disk.location == "/dev/disk4"


def test_app_version():
    app = App(Stub(ventoy_version="1.1.5"))

    assert app.version == "1.1.5"


def test_app_workdir():
    app = App(workdir="/tmp")
    assert app.workdir == Path("/tmp")


def test_app_images(fixtures_path):
    app = App(
        downloader=Stub(ventoy_dir=(fixtures_path / "fake_images")),
        workdir="/tmp"
    )

    assert len(app.images) == 3
    assert all([isinstance(img, DiskImage) for img in app.images.values()])


def test_chmod(tmp_path):
    """
    drwxr-xr-x 18 alissa staff 576  Apr 23 04:04 ventoy-1.1.12
    -rw-r--r--  1 alissa staff 2.6K Apr 23 04:04 ventoy-1.1.12/README
    -rwxr-xr-x  1 alissa staff 2.4K Apr 23 04:04 ventoy-1.1.12/Ventoy2Disk.sh
    """

    # relpath -> (old permission, new permission)
    # a small sample of files in the extracted dir
    # (old permission is just for reference)
    files = {
        "ventoy-1.1.12": (0o40755, 0o40777),
        "ventoy-1.1.12/README": (0o100644, 0o100666),
        "ventoy-1.1.12/Ventoy2Disk.sh": (0o100755, 0o100777),
    }

    app = App(args=Stub(work_dir=tmp_path, ventoy_version="1.1.12"))
    copy_fixture("ventoy-1.1.12-linux.tar.gz", tmp_path)

    app.downloader.extract()

    app.chmod()

    for name, (old, new) in files.items():
        path = tmp_path / name
        mode = path.stat().st_mode
        _mode = oct(mode)

        assert mode == new, f"{name}: Expected mode: {new:#o} but got {_mode}"


#  def test_app_():
#      ...
