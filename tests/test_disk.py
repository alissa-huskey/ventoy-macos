import pytest

from tests.data import diskutil_info_plist, diskutil_list_plist
from ventoy_macos import disk as disk_module
from ventoy_macos.disk import Disk
from ventoy_macos.object import Object as Stub
from ventoy_macos.partition import Partition

bp = breakpoint


COMMANDS = []


def run(args, **kwargs):
    """Mock run command."""
    COMMANDS.append(args)
    return Stub(returncode=0)


def test_disk():
    disk = Disk()
    assert disk


def test_disk_info(monkeypatch):
    expected = {
        'Bootable': False,
        'BusProtocol': 'USB',
        'CanBeMadeBootable': False,
        'CanBeMadeBootableRequiresDestroy': False,
        'Content': 'FDisk_partition_scheme',
        'DeviceBlockSize': 512,
        'DeviceIdentifier': 'disk4',
        'DeviceNode': '/dev/disk4',
        'DeviceTreePath':
            'IODeviceTree:/arm-io/usb-drd1@2280000/usb-drd1-port-hs@01100000',
        'Ejectable': True,
        'EjectableMediaAutomaticUnderSoftwareControl': True,
        'EjectableOnly': True,
        'FreeSpace': 0,
        'GlobalPermissionsEnabled': False,
        'IOKitSize': 8178892800,
        'IORegistryEntryName': 'Generic Flash Disk Media',
        'Internal': False,
        'LowLevelFormatSupported': False,
        'MediaName': 'Flash Disk',
        'MediaType': 'Generic',
        'MountPoint': '',
        'OS9DriversInstalled': False,
        'OSInternalMedia': False,
        'ParentWholeDisk': 'disk4',
        'PartitionMapPartition': False,
        'RAIDMaster': False,
        'RAIDSlice': False,
        'Removable': True,
        'RemovableMedia': True,
        'RemovableMediaOrExternalDevice': True,
        'SMARTDeviceSpecificKeysMayVaryNotGuaranteed': {},
        'SMARTStatus': 'Not Supported',
        'Size': 8178892800,
        'SupportsGlobalPermissionsDisable': False,
        'SystemImage': False,
        'TotalSize': 8178892800,
        'VirtualOrPhysical': 'Physical',
        'VolumeName': '',
        'VolumeSize': 0,
        'WholeDisk': True,
        'Writable': True,
        'WritableMedia': True,
        'WritableVolume': False
    }

    with monkeypatch.context() as m:
        m.setattr("subprocess.check_output", lambda args: diskutil_info_plist)
        disk = Disk("/dev/disk3")

        assert disk.info == expected


def test_disk_sectors(monkeypatch):
    info = {"TotalSize": "5368664064"}

    disk = Disk("/dev/disk4")
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
    ({"Internal": True, "Removable": False}, False),
    ({"Internal": False, "Removable": True}, True),
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
    info = {"TotalSize": "5368664064"}

    disk = Disk()
    with monkeypatch.context() as m:
        m.setattr(disk, "info", info)

        assert disk.gb == 4.999958038330078


def test_disk_current_layout(monkeypatch):
    expected = [
        Partition(
            number=1,
            name="NO NAME",
            format="DOS_FAT_32",
            bytes=8173993984,
            identifier="disk4s1",
        ),
    ]

    disk = Disk("/dev/disk4")

    with monkeypatch.context() as m:
        m.setattr("subprocess.check_output", lambda args: diskutil_list_plist)
        assert disk.current_layout == expected


def test_disk_planned_layout(planned_layout, sectors_64g):
    disk = Disk()
    disk.sectors = sectors_64g

    assert disk.planned_layout == planned_layout


@pytest.mark.parametrize(["offset", "is_correct"], [
    ("2048", True),
    ("92423", False),
])
def test_disk_verify(monkeypatch, offset, is_correct):
    info = {"Offset": offset}

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
