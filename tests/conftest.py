from pathlib import Path
from string import ascii_lowercase

import pytest

from ventoy_macos.disk import Disk
from ventoy_macos.partition import Partition


@pytest.fixture
def sectors_64g():
    """Return the number of sectors for a 64GB disk."""
    return 125000000


@pytest.fixture
def fixtures_path() -> Path:
    """Return the path to the fixtures directory."""
    return Path(__file__).parent / "fixtures"


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
