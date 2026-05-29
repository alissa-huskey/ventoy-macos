from pathlib import Path
from string import ascii_lowercase

import pytest

from ventoy_macos import logger as logger_module
from ventoy_macos.disk import Disk
from ventoy_macos.partition import Partition

bp = breakpoint


@pytest.fixture
def sectors_64g():
    """Return the number of sectors for a 64GB disk."""
    return 125000000


@pytest.fixture
def planned_layout():
    """Planned partition layout for a 64G drive."""
    return [
        Partition(
            number=1,
            name="Ventoy",
            fs="exFAT",
            start=2048,
            end=124934423,
        ),
        Partition(
            number=2,
            name="VTOYEFI",
            fs="FAT16",
            start=124934424,
            end=124999959,
        ),
    ]


@pytest.fixture
def fake_disk(fs):
    """Return a Disk object that exists on a fake filesystem."""
    disk = Disk("/dev/disk67")
    fs.create_file(disk.raw_location, contents=ascii_lowercase + "x" * 512)

    return disk


@pytest.fixture
def markers(request):
    """Return a list of marker names for the currently running test."""
    return [m.name for m in request.node.iter_markers()]


@pytest.fixture(autouse=True)
def disable_logger(monkeypatch, markers):
    """Ensure logs don't print to stdout or workdir."""
    with monkeypatch.context() as m:
        if "enable_logging" not in markers:
            m.setattr(logger_module.Logger, "ENABLE", False)
        yield
