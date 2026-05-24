from pathlib import Path

from tests import Stub
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
    assert app.disk.device == "/dev/disk4"


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


#  def test_app_():
#      ...
