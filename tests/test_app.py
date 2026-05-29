from tests import Stub
from ventoy_macos.app import App, Workdir
from ventoy_macos.disk import Disk

bp = breakpoint


def test_app():
    assert App()


def test_app_workdir():
    app = App(Stub(dir=str("/tmp")))

    assert app.workdir == Workdir(path="/tmp")


def test_app_workdir_null(monkeypatch, tmp_path):
    with monkeypatch.context() as m:
        m.setattr(Workdir, "TMPDIR", tmp_path)

        app = App()
        assert app.workdir == Workdir()


def test_app_disk():
    app = App(Stub(disk="/dev/disk4"))

    assert isinstance(app.disk, Disk)
    assert app.disk.location == "/dev/disk4"


def test_app_version():
    app = App(Stub(ventoy_version="1.1.5"))

    assert app.version == "1.1.5"


#  def test_app_():
#      ...
