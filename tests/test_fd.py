import os
from string import ascii_lowercase

import pytest

from ventoy_macos.disk import Disk
from ventoy_macos.fd import FD

bp = breakpoint


@pytest.fixture
def fake_disk(fs):
    """Return a Disk object that exists on a fake filesystem."""
    disk = Disk("/dev/disk67")
    fs.create_file(disk.raw_device, contents=ascii_lowercase + "x" * 512)

    return disk


@pytest.fixture
def fd(fake_disk) -> FD:
    """Yield and open FD object then close it."""
    fd = FD(fake_disk)
    fd.open()

    yield fd

    fd.close()


def test_fd():
    fd = FD()
    assert fd


def test_fd_open(fake_disk):
    fd = FD(fake_disk)
    fd.open()

    assert fd.id == 3
    assert fd.is_open is True


def test_fd_open_context_manager(fake_disk):
    fd = FD(fake_disk)

    with fd.open() as f:
        assert f == fd
        assert f.id == fd.id
        assert f.is_open is True

    assert fd.is_open is False


def test_fd_close(fake_disk):
    fd = FD(fake_disk)
    fd.open()

    fd.close()

    assert fd.is_open is False


@pytest.mark.skip("not sure if this is broken")
def test_fd_seek(fd):
    position = fd.seek(5)

    assert position == 5


def test_fd__write(fd):
    fd._write(b"ABC")
    os.lseek(fd.id, 0, os.SEEK_SET)
    data = os.read(fd.id, 6)
    assert data == b"ABCdef"


def test_fd_write(fd):
    fd.write(3, b"DEF")
    fd.seek(0)
    data = os.read(fd.id, 6)
    assert data == b"abcDEF"


def test_fd_save(fd):
    # just tests for errors
    fd.save()


def test_fd__read(fd):
    data = fd._read(3)

    assert data == b"abc"


def test_fd_read(fd):
    data = fd.read(3, 3)

    assert data == b"def"


def test_fd_patch(fd):
    fd.patch(1, 3, b"XYZ")
    data = fd.read(512, 9)
    assert data == b"xxxXYZxxx"


#  @pytest.mark.skip
#  def test_fd_():
#      ...
