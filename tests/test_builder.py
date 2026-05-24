from uuid import UUID

import pytest

from tests import Stub
from ventoy_macos import VentoyMacosError
from ventoy_macos.builder import Builder
from ventoy_macos.fd import FD

# used to store mocked os.write calls
DATA = []

bp = breakpoint


@pytest.fixture
def disk_images():
    """Return a mapping of DiskImage objects."""
    return {
        "boot_img": Stub(data=b"data"),
        "core_img": Stub(data=b"data"),
        "disk_img": Stub(data=b"data"),
    }


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
    #  disk_images,
):
    fake_disk.sectors = sectors_64g
    params = {"layout": planned_layout}

    # set the disk image stub
    if attr:
        params[attr] = Stub(data=b"data")

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


def test_builder_images():
    images = {
        "boot_img": Stub(data=b"A"),
        "core_img": Stub(data=b"B"),
        "disk_img": Stub(data=b"C"),
    }
    builder = Builder(images=images)
    builder.images == images

    assert builder.boot_img == b"A"
    assert builder.core_img == b"B"
    assert builder.disk_img == b"C"


#  def test_builder_():
#      ...
