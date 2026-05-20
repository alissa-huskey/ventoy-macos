import pytest

from ventoy_macos import disk as disk_module
from ventoy_macos.disk import Disk
from ventoy_macos.object import Object as Stub

bp = breakpoint


COMMANDS = []


def run(args, **kwargs):
    """Mock run command."""
    COMMANDS.append(args)
    return Stub(returncode=0)


def test_disk():
    disk = Disk()
    assert disk


def test_disk_info():
    disk = Disk("/dev/disk3")
    info = disk.info

    assert isinstance(info, dict)

    assert info["is apfs container"] is True
    assert info["device identifier"] == "disk3"
    assert info["device node"] == "/dev/disk3"

    assert "disk size" in info


def test_disk_sectors(monkeypatch):
    info = {"disk size": "5.4 GB (5368664064 Bytes) (exactly 10485672 512-Byte-Units)"}

    disk = Disk()
    with monkeypatch.context() as m:
        m.setattr(disk, "info", info)

        assert disk.sectors == 10485672


@pytest.mark.parametrize(["location", "exists"], [
    ("/dev/disk1", True),
    ("/dev/skjdfslkfj", False),
])
def test_disk_exists(location, exists):
    disk = Disk(location)
    assert disk.exists() is exists


@pytest.mark.parametrize(["info", "is_external"], [
    ({"device location": "Internal", "removable media": "Fixed"}, False),
    ({"device location": "External", "removable media": "removable"}, True),
])
def test_disk_is_external(monkeypatch, info, is_external):
    disk = Disk()

    with monkeypatch.context() as m:
        m.setattr(disk, "info", info)

        assert disk.is_external() is is_external


@pytest.mark.parametrize(["location", "is_disk"], [
    ("/dev/disk0", True),
    ("/dev/disk1", True),
    ("/dev/console", False),
    ("/dev/disk87", False),
])
def test_disk_is_disk(location, is_disk):
    disk = Disk(location)
    assert disk.is_disk() is is_disk


@pytest.mark.parametrize(["location", "is_system_disk"], [
    ("/dev/console", False),
    ("/dev/disk0", True),
    ("/dev/disk1", True),
    ("/dev/disk4", False),
])
def test_disk_is_system_disk(location, is_system_disk):
    disk = Disk(location)
    assert disk.is_system_disk() is is_system_disk


def test_disk_name():
    disk = Disk("/dev/disk2")
    assert disk.name == "disk2"


def test_disk_raw_device():
    disk = Disk("/dev/disk4")
    assert disk.raw_device == "/dev/rdisk4"


def test_disk_gb(monkeypatch):
    info = {"disk size": "5.4 GB (5368664064 Bytes) (exactly 10485672 512-Byte-Units)"}

    disk = Disk()
    with monkeypatch.context() as m:
        m.setattr(disk, "info", info)

        assert disk.gb == 4.999958038330078


def test_disk_current_layout(monkeypatch):
    layout = """
/dev/disk3 (synthesized):
   #:                       TYPE NAME                    SIZE       IDENTIFIER
   0:      APFS Container Scheme -                      +2.0 TB     disk3
                                 Physical Store disk0s2
   1:                APFS Volume Macintosh HD            13.2 GB    disk3s1
   2:              APFS Snapshot com.apple.os.update-... 13.2 GB    disk3s1s1
   3:                APFS Volume Preboot                 12.5 GB    disk3s2
   4:                APFS Volume Recovery                2.0 GB     disk3s3
   5:                APFS Volume Data                    484.0 GB   disk3s5
   6:                APFS Volume VM                      5.4 GB     disk3s6
   7:                APFS Volume Nix Store               1.3 GB     disk3s7
"""
    disk = Disk()

    with monkeypatch.context() as m:
        m.setattr(disk_module, "run", lambda args: Stub(stdout=layout))
        assert disk.current_layout == layout


def test_disk_planned_layout(planned_layout, sectors_64g):
    disk = Disk()
    disk.sectors = sectors_64g

    assert disk.planned_layout == planned_layout


@pytest.mark.parametrize(["offset", "is_correct"], [
    ("2048", True),
    ("92423", False),
])
def test_disk_verify(monkeypatch, offset, is_correct):
    info = {"offset": offset}

    disk = Disk()
    with monkeypatch.context() as m:
        m.setattr(disk, "info", info)

        assert disk.verify() is is_correct


def test_disk_mount(monkeypatch):
    with monkeypatch.context() as m:
        m.setattr(disk_module, "run", run)
        disk = Disk("/dev/disk67")
        disk.mount()

        assert COMMANDS.pop() == ["diskutil", "mountDisk", "/dev/disk67"]


def test_disk_unmount(monkeypatch):
    with monkeypatch.context() as m:
        m.setattr(disk_module, "run", run)
        disk = Disk("/dev/disk67")
        disk.unmount()

        assert COMMANDS.pop() == ["diskutil", "unmountDisk", "force", "/dev/disk67"]


def test_disk_format(monkeypatch):
    with monkeypatch.context() as m:
        m.setattr(disk_module, "run", run)
        device = "/dev/disk67s1"
        disk = Disk(device)
        success = disk.format()

        assert success
        assert COMMANDS.pop() == ["newfs_exfat", "-v", "Ventoy", device]


#  def test_disk_():
#      """
#      GIVEN: ...
#      WHEN: ...
#      THEN: ...
#      """
