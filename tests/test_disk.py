import pytest

from tests.data import diskutil_list_plist
from ventoy_macos.disk import Disk
from ventoy_macos.partition import Partition

bp = breakpoint


def test_disk():
    disk = Disk()
    assert disk


def test_disk_list(monkeypatch):
    expected = [
        {
            "Content": "DOS_FAT_32",
            "DeviceIdentifier": "disk8s1",
            "MountPoint": "/Volumes/NO NAME",
            "Size": 8173993984,
            "VolumeName": "NO NAME",
            "VolumeUUID": "03F98CF3-F2DC-3581-90A3-3F5FE8A0A60D"
        },
    ]

    with monkeypatch.context() as m:
        m.setattr("subprocess.check_output", lambda args: diskutil_list_plist)
        disk = Disk("/dev/disk3")

        assert disk.list == expected


@pytest.mark.parametrize(["location", "is_disk"], [
    ("/dev/disk0", True),
    ("/dev/disk1", True),
    ("/dev/console", False),
    ("/dev/disk87", False),
])
def test_disk_is_disk(location, is_disk):
    disk = Disk(location, info={})
    assert disk.is_disk() is is_disk


@pytest.mark.parametrize(["location", "is_system_disk"], [
    ("/dev/console", False),
    ("/dev/disk0", True),
    ("/dev/disk1", True),
    ("/dev/disk4", False),
])
def test_disk_is_system_disk(location, is_system_disk):
    disk = Disk(location, info={})
    assert disk.is_system_disk() is is_system_disk


def test_disk_raw_location():
    disk = Disk("/dev/disk4")
    assert disk.raw_location == "/dev/rdisk4"


def test_disk_partitions(monkeypatch):
    disk = Disk("/dev/disk8")
    expected = [
        Partition(
            location="/dev/disk8s1",
            number=1,
            parent=disk,
        ),
    ]

    with monkeypatch.context() as m:
        m.setattr("subprocess.check_output", lambda args: diskutil_list_plist)
        assert disk.partitions == expected


def test_disk_planned_layout(planned_layout, sectors_64g):
    disk = Disk()
    disk.sectors = sectors_64g

    assert disk.planned_layout == planned_layout


#  def test_disk_():
#      """
#      GIVEN: ...
#      WHEN: ...
#      THEN: ...
#      """
