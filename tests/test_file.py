import pytest  # noqa F401

from ventoy_macos.file import File

bp = breakpoint


def test_file():
    assert File()


def test_file_exists(shared_datadir):
    file = File(shared_datadir / "ventoy-1.1.12-linux.tar.gz")
    assert file.exists()


def test_file_size(shared_datadir):
    file = File(shared_datadir / "fake_images" / "boot.img")
    assert file.size == 9


def test_file_read(shared_datadir):
    path = (shared_datadir / "fake_images" / "boot.img")
    img = File(path)
    data = img.read()
    assert data == b"boot img\n"


def test_file_data(shared_datadir):
    path = (shared_datadir / "fake_images" / "boot.img")
    img = File(path)
    assert img.data == b"boot img\n"


#  @pytest.mark.skip
#  def test_file_():
#      ...
