from string import ascii_lowercase

import pytest

from tests import noop
from ventoy_macos import logger as logger_module
from ventoy_macos.disk import Disk
from ventoy_macos.partition import Partition

bp = breakpoint


@pytest.fixture
def pop_responses():
    """Return a mock to return the first popped value from an iter."""
    def mk_mock(responses, func=noop):
        """Return a mock function."""
        def mock(*args, **kwargs):
            """Call the function then return the first value from responses."""
            func(*args, **kwargs)
            return responses.pop(0)
        return mock
    return mk_mock


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
