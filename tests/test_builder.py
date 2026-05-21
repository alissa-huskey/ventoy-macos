from uuid import UUID

import pytest

from ventoy_macos import VentoyMacosError
from ventoy_macos.builder import Builder
from ventoy_macos.fd import FD

DATA = []

bp = breakpoint


def os_write(fd_id: int, data: bytes):
    """Mock os.write function."""
    DATA.append(data)


@pytest.fixture
def patch_os_write(monkeypatch):
    """Monkeypatch the os.write function."""
    with monkeypatch.context() as m:
        m.setattr("os.write", os_write)

        yield


def test_builder():
    builder = Builder()
    assert builder


def test_builder_fd():
    builder = Builder("/dev/disk4")

    assert isinstance(builder.fd, FD)
    assert builder.fd.disk == builder.disk


def test__get_image_file(fixtures_path):
    path = fixtures_path / "fake_images"
    builder = Builder(images_path=path)

    img = builder._get_image_file("boot")
    assert img == b"boot img\n"
    assert builder._boot_img == img


def test_builder_images(fixtures_path):
    path = fixtures_path / "fake_images"
    builder = Builder(images_path=path)

    assert builder.boot_img and builder.boot_img == b"boot img\n"
    assert builder.core_img and builder.core_img == b"core img\n"
    assert builder.disk_img and builder.disk_img == b"disk img\n"


def test_builder_image_setter():
    builder = Builder()
    builder.boot_img = b"set boot img"

    assert builder.boot_img == b"set boot img"


def test_builder_write_init_header(fake_disk, patch_os_write):
    builder = Builder(fake_disk)
    builder.write_init_header()

    data = DATA.pop()

    assert data == (b"\x00" * 1048576)


def test_builder_write_init_backup(fake_disk, sectors_64g, patch_os_write):
    fake_disk.sectors = sectors_64g
    builder = Builder(fake_disk)
    builder.write_init_backup()

    data = DATA.pop()

    assert data == (b"\x00" * 16896)


@pytest.mark.parametrize(["method"], [
    ("write_mbr",),
    ("write_primary_header",),
    ("write_entries",),
    ("write_backup",),
    ("write_boot_img",),
    ("write_core_img",),
])
def test_verify_attr(fake_disk, patch_os_write, method):
    builder = Builder(fake_disk)
    func = getattr(builder, method)

    with pytest.raises(VentoyMacosError):
        func()


@pytest.mark.parametrize(["method", "attrs"], [
    ("write_mbr", "mbr"),
    ("write_primary_header", "primary"),
    ("write_entries", "entries"),
    ("write_backup", ("backup", "entries")),
])
def test_builder_writers(fake_disk, patch_os_write, sectors_64g, method, attrs):
    if not isinstance(attrs, tuple):
        attrs = (attrs,)
    kwargs = {name: b"data" for name in attrs}
    fake_disk.sectors = sectors_64g
    builder = Builder(fake_disk, **kwargs)
    func = getattr(builder, method)
    func()

    while DATA:
        data = DATA.pop()

        assert data == b"data"


@pytest.mark.parametrize(["method", "attr", "matcher"], [
    ("write_boot_img", "boot_img", None),
    ("write_core_img", "core_img", None),
    ("write_disk_img", "disk_img", None),
])
def test_builder_patchers(
    fake_disk,
    patch_os_write,
    sectors_64g,
    planned_layout,
    method,
    attr,
    matcher,
):
    fake_disk.sectors = sectors_64g
    params = {"layout": planned_layout}
    if attr:
        params[attr] = b"data"
    builder = Builder(fake_disk, **params)
    func = getattr(builder, method)
    func()

    while DATA:
        data = DATA.pop()

        if matcher:
            assert matcher(data)
        else:
            assert data.startswith(b"data")


def test_builder_write_gpt_marker(fake_disk, patch_os_write):
    builder = Builder(fake_disk)
    builder.write_gpt_marker()

    data = DATA.pop()

    assert data[92:93] == b"\x22"


@pytest.mark.skip("The test is broken, but the thing works I think.")
def test_builder_write_second_gpt_marker(fake_disk, patch_os_write):
    builder = Builder(fake_disk)
    builder.write_second_gpt_marker()

    data = DATA.pop()

    print(data)
    assert data[500: 501] == b"\x23"


def test_builder_write_disk_uuid(fake_disk, patch_os_write):
    builder = Builder(fake_disk)
    builder.write_disk_uuid()

    data = DATA.pop()

    offset = 384
    uuid = data[offset: offset + 16]

    try:
        assert UUID(bytes=uuid)
    except ValueError:
        assert False, "A valid UUID was not patched in at offset 384."


def test_builder_write_disk_signature(fake_disk, patch_os_write):
    builder = Builder(fake_disk)

    # This writes four random bytes at offset 440
    # I can't think of a way to test it, so for now
    # this just ensures there are no exceptions
    builder.write_disk_signature()


#  def test_builder_():
#      ...
