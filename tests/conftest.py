from pathlib import Path
from string import ascii_lowercase

import pytest

from ventoy_macos.disk import Disk


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
    return {
        "part1_start": 2048,
        "part1_end": 124934423,
        "part1_sectors": 124932376,
        "part2_start": 124934424,
        "part2_end": 124999959,
        "part2_sectors": 65536,
    }


@pytest.fixture
def fake_disk(fs):
    """Return a Disk object that exists on a fake filesystem."""
    disk = Disk("/dev/disk67")
    fs.create_file(disk.raw_device, contents=ascii_lowercase + "x" * 512)

    return disk
