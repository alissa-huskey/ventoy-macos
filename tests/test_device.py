import pytest

from tests import COMMANDS, mock_run
from tests.data import diskutil_info_plist
from ventoy_macos import device as device_module
from ventoy_macos.device import Device
from ventoy_macos.object import Object as Stub

bp = breakpoint


def test_device():
    assert Device()


def test_device_id():
    device = Device("/dev/disk2")
    assert device.id == "disk2"


def test_device_name():
    device = Device("/dev/disk3", info={"MediaName": "Flash Disk"})
    assert device.name == "Flash Disk"


@pytest.mark.parametrize(["location", "exists"], [
    ("/dev/disk1", True),
    ("/dev/skjdfslkfj", False),
])
def test_device_exists(location, exists):
    device = Device(location)
    assert device.exists() is exists


def test_device_info(monkeypatch):
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
        device = Device("/dev/disk3")

        assert device.info == expected


def test_device_mount(monkeypatch):
    with monkeypatch.context() as m:
        m.setattr(device_module, "run", mock_run)
        device = Device("/dev/disk67")
        device.mount()

        assert COMMANDS.pop() == ["diskutil", "mountDisk", "/dev/disk67"]


def test_device_unmount(monkeypatch):
    with monkeypatch.context() as m:
        m.setattr(device_module, "run", mock_run)
        device = Device("/dev/disk67")
        device.unmount()

        assert COMMANDS.pop() == ["diskutil", "unmountDisk", "force", "/dev/disk67"]


def test_device_format_newfs(monkeypatch):
    with monkeypatch.context() as m:
        m.setattr(device_module, "run", mock_run)
        device = Device("/dev/disk67s1")
        success = device.format()

        assert success
        assert COMMANDS.pop() == ["newfs_exfat", "-v", "Ventoy", device.location]


def test_device_format_diskutil(monkeypatch):
    RESULTS = [
        Stub(returncode=1),
        Stub(returncode=0),
    ]

    def mock_run(args, **kwargs):
        """Mock run command."""
        COMMANDS.append(args)
        return RESULTS.pop(0)

    with monkeypatch.context() as m:
        m.setattr(device_module, "run", mock_run)
        device = Device("/dev/disk67s1")
        success = device.format()

        assert success
        assert COMMANDS.pop() == [
            "diskutil",
            "eraseVolume",
            "ExFAT",
            "Ventoy",
            device.location,
        ]


def test_device_sectors():
    device = Device("/dev/disk4", size=5368664064)
    assert device.sectors == 10485672


@pytest.mark.parametrize(["info", "keys", "default", "expected", "msg"], [
    # should return False, not None
    (
        {"Ejectable": False, "EjectableOnly": False},
        ["EjectableMediaAutomaticUnderSoftwareControl", "Ejectable", "EjectableOnly"],
        None, False,
        "Should return False not None",
    ),
    (None, ["a", "b"], None, None, "Should return None if not found."),
    (
        {"a": "", "b": 1}, ["a", "b"], None, 1,
        "Should not return empty strings",
    ),
    (
        {"a": 1, "b": 2}, ["a", "b"], None, 1, "Should return first found"
    ),
    (
        {}, ["a"], 1, 1, "Should return default if passed when not found",
    )
])
def test_device_info_get(info, keys, default, expected, msg):
    device = Device(info=info)
    result = device.info_get(*keys, default=default)

    assert result == expected, msg


@pytest.mark.parametrize(["info", "is_external"], [
    ({"Internal": True, "Removable": False}, False),
    ({"Internal": False, "Removable": True}, True),
])
def test_device_is_external(monkeypatch, info, is_external):
    with monkeypatch.context() as m:
        device = Device()
        m.setattr(device, "info", info)
        device.is_external()

        assert device.is_external() is is_external


def test_device_gb():
    device = Device(size=5368664064)
    assert device.gb == 4.999958038330078


def test_device_scheme():
    device = Device(info={"Content": "GUID_partition_scheme"})
    assert device.scheme == "GUID_partition_scheme"


def test_device_size():
    device = Device(info={"Size": 5368664064})
    assert device.size == 5368664064


@pytest.mark.parametrize(["info", "expected"], [
    ({"PartitionMapPartition": True, "WholeDisk": False}, True),
    ({"PartitionMapPartition": False, "WholeDisk": True}, False),
])
def test_device_is_partition(info, expected):
    device = Device(info=info)
    assert device.is_partition() is expected


@pytest.mark.parametrize(["info", "expected"], [
    ({"FilesystemType": "exfat"}, "exfat"),
    ({"Content": "Microsoft Basic Data"}, "Microsoft Basic Data"),
    (
        {
            "FilesystemName": "ExFAT",
            "Content": "Microsoft Basic Data",
        },
        "ExFAT (Microsoft Basic Data)",
    ),
])
def test_device_fs(info, expected):
    device = Device(info=info)
    assert device.fs == expected


#  @pytest.mark.skip
#  def test_device_():
#      ...
