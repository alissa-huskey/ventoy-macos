import pytest  # noqa F401

from ventoy_macos.file import File

bp = breakpoint


def test_file():
    assert File()


def test_file_exists(fixtures_path):
    file = File(fixtures_path / "ventoy-1.1.12-linux.tar.gz")
    assert file.exists()


def test_file_size(fixtures_path):
    file = File(fixtures_path / "fake_images" / "boot.img")
    assert file.size == 9


def test_file_read(fixtures_path):
    path = (fixtures_path / "fake_images" / "boot.img")
    img = File(path)
    data = img.read()
    assert data == b"boot img\n"


def test_file_data(fixtures_path):
    path = (fixtures_path / "fake_images" / "boot.img")
    img = File(path)
    assert img.data == b"boot img\n"


#  @pytest.mark.skip
#  def test_file_():
#      ...
