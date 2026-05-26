"""Disk operations."""

import plistlib
import subprocess
from functools import cached_property
from pathlib import Path
from re import compile as re_compile

from attr import attr, hasattrs

from ventoy_macos import SECTOR_SIZE as _SECTOR_SIZE
from ventoy_macos import VentoyMacosError
from ventoy_macos.common import b2s, run, s2b, s2g
from ventoy_macos.object import Object
from ventoy_macos.partition import Partition

bp = breakpoint


@hasattrs
class Disk(Object):
    """A disk object."""

    SECTOR_NUM = 65536  # 32MB for EFI partition
    SECTOR_SIZE = _SECTOR_SIZE
    SIZE_RE = re_compile(r'\((\d+) Bytes\)')

    def __init__(self, device: str = None, **kwargs):
        """Initialize object."""
        self.device = device
        super().__init__(**kwargs)

    def __str__(self):
        """Return a human readable string."""
        return self.device or "Disk()"

    @cached_property
    def name(self) -> bool:
        """Return the disk identifier."""
        if not self.device:
            return
        return self.device.removeprefix("/dev/")

    @property
    def raw_device(self) -> str:
        """Return the raw device identifier."""
        if not self.device:
            return
        return self.device.replace("/dev/disk", "/dev/rdisk")

    def exists(self) -> bool:
        """Return True if the disk exists."""
        return self.device and Path(self.device).exists()

    def is_disk(self) -> bool:
        """Return True if it is a /dev/diskX that exists."""
        return self.device.startswith("/dev/disk") and self.exists()

    def is_system_disk(self) -> bool:
        """Return True if disk is likely a system disk."""
        return self.name in ("disk0", "disk1")

    def is_external(self) -> bool:
        """Return True if the disk is external."""
        return (
            self.info.get("Removable", False) and
            not self.info.get("Internal", True)
        )

    @cached_property
    def info(self) -> dict:
        """Return the diskutil info."""
        if not self.exists():
            return {}

        raw = subprocess.check_output(["diskutil", "info", "-plist", self.device])
        data = plistlib.loads(raw)

        return data

    @attr
    def sectors(self) -> int:
        """Return the disk size in 512-byte-units."""
        if not self._sectors and self.info:
            try:
                self._sectors, _ = b2s(int(self.info["TotalSize"]))
            # if the "Size" key is missing, or the value is not a valid int
            except (KeyError, ValueError):
                raise VentoyMacosError(f"Could not determine size of {self.device}")

        return self._sectors

    @property
    def gb(self) -> float:
        """Return the disk size in GB."""
        return s2g(self.sectors)

    @property
    def current_layout(self):
        """Return the current partition layout."""
        raw = subprocess.check_output(["diskutil", "list", "-plist", self.device])
        data = plistlib.loads(raw)
        partitions = data["AllDisksAndPartitions"][0].get("Partitions", [])
        layout = []

        for i, part in enumerate(partitions, 1):
            id = part.get("DeviceIdentifier", "")
            disk = self.__class__(f"/dev/{part.get('DeviceIdentifier', '')}")

            obj = Partition(
                number=i,
                name=part.get("VolumeName", ""),
                format=disk.info.get(
                    "FilesystemUserVisibleName",
                    part.get("Content", ""),
                ),
                identifier=id,
                bytes=part.get("Size", ""),
                disk=disk,
            )
            layout.append(obj)
        return layout

    @cached_property
    def planned_layout(self):
        """Calculate Ventoy-compatible partition layout."""
        # partition for disk images
        # total disk size minus ~32M for the Ventoy partition
        part1 = Partition(
            number=1,
            name="Ventoy",
            format="exFAT",
            start=2048,   # 1MB - Ventoy requirement
            end=(self.sectors - self.SECTOR_NUM - 34),
        )

        # bootable Ventoy partition
        part2 = Partition(
            number=2,
            name="VTOYEFI",
            format="FAT16",
            start=part1.end + 1,
        )

        # jump back to the start of the byte
        mod = part2.start % 8
        if mod > 0:
            part1.end -= mod
            part2.start = part1.end + 1

        part2.end = part2.start + self.SECTOR_NUM - 1

        return [part1, part2]

    def verify(self) -> bool:
        """Verify the partition 1 offset starts at sector 2048."""
        return self.info and self.info.get("PartitionMapPartitionOffset") == s2b(2048)

    def mount(self):
        """Mount the disk."""
        run(["diskutil", "mountDisk", self.device], check=False)

    def unmount(self):
        """Mount the disk."""
        run(["diskutil", "unmountDisk", "force", self.device], check=False)

    def format(self):
        """Format the disk."""
        result = run(["newfs_exfat", "-v", "Ventoy", self.device], check=False)
        if result.returncode != 0:
            result = run(["diskutil", "eraseVolume", "ExFAT", "Ventoy", self.device])
        return result.returncode == 0
