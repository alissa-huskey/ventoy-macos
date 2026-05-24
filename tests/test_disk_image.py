from pathlib import Path

import pytest  # noqa F401

from ventoy_macos.disk_image import DiskImage

bp = breakpoint


def test_disk_image():
    assert DiskImage()


def test_disk_image_id():
    img = DiskImage(name="boot")
    assert img.id == "boot_img"


def test_disk_image_source():
    path = Path("/tmp")
    img = DiskImage(source_dir=path, relpath=("boot", "boot.img"))
    assert img.source.path == path / "boot" / "boot.img"


def test_disk_image_dest():
    path = Path("/tmp")
    img = DiskImage(dest_dir=path, relpath=("boot", "core.img.xz"))
    assert img.dest.path == path / "core.img"


def test_disk_image_data(fixtures_path):
    path = (fixtures_path / "fake_images" / "boot.img")
    img = DiskImage(name="boot", dest=path)
    assert img.data == b"boot img\n"


def test_disk_image_size(fixtures_path):
    path = (fixtures_path / "fake_images" / "boot.img")
    img = DiskImage(name="boot", dest=path)
    assert img.size == 9


@pytest.mark.parametrize("relpath", [
    ("boot", "core.img.xz"),
    ("boot", "boot.img"),
    ("ventoy", "ventoy.disk.img.xz"),
])
def test_disk_image_decompress(tmp_path, fixtures_path, relpath):
    img = DiskImage(
        source_dir=(fixtures_path / "ventoy-1.1.12"),
        dest_dir=tmp_path,
        relpath=relpath,
    )

    img.decompress()

    assert img.dest.exists()


#  @pytest.mark.skip
#  def test_disk_image_():
#      ...
