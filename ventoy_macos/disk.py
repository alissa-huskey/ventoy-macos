"""Disk operations."""

import plistlib
import subprocess
from functools import cached_property
from re import compile as re_compile

from attr import attr, hasattrs

from ventoy_macos import SECTOR_SIZE as _SECTOR_SIZE
from ventoy_macos import VentoyMacosError
from ventoy_macos.device import Device
from ventoy_macos.partition import Partition

bp = breakpoint


@hasattrs
class Disk(Device):
    """A disk object."""

    SECTOR_NUM = 65536  # 32MB for EFI partition
    SECTOR_SIZE = _SECTOR_SIZE
    SIZE_RE = re_compile(r'\((\d+) Bytes\)')

    @property
    def raw_location(self) -> str:
        """Return the raw location identifier."""
        if not self.location:
            return
        return self.location.replace("/dev/disk", "/dev/rdisk")

    def is_disk(self) -> bool:
        """Return True if it is a /dev/diskX that exists."""
        if self.is_partition():
            return False
        return self.location.startswith("/dev/disk") and self.exists()

    def is_system_disk(self) -> bool:
        """Return True if disk is likely a system disk."""
        if self.info and self.info.get("SystemImage"):
            return True
        return self.id in ("disk0", "disk1")

    @cached_property
    def list(self) -> dict:
        """Return the diskutil list data."""
        raw = subprocess.check_output(["diskutil", "list", "-plist", self.location])
        data = plistlib.loads(raw)
        try:
            info = data.get("AllDisksAndPartitions", [])[0]
        except IndexError:
            return []
        return info.get("Partitions", [])

    @attr
    def partitions(self):
        """Return the current partition layout."""
        if self._partitions is None:
            layout = []

            for i, part in enumerate(self.list, 1):
                id = part.get("DeviceIdentifier", "")
                if not id:
                    raise VentoyMacosError("No partition id for this partition.")

                layout.append(Partition(f"/dev/{id}", number=i, parent=self))
            self._partitions = layout

        return self._partitions

    @cached_property
    def planned_layout(self):
        """Calculate Ventoy-compatible partition layout."""
        # partition for disk images
        # total disk size minus ~32M for the Ventoy partition
        part1 = Partition(
            number=1,
            name="Ventoy",
            fs="exFAT",
            start=2048,   # 1MB - Ventoy requirement
            end=(self.sectors - self.SECTOR_NUM - 34),
        )

        # bootable Ventoy partition
        part2 = Partition(
            number=2,
            name="VTOYEFI",
            fs="FAT16",
            start=part1.end + 1,
        )

        # jump back to the start of the byte
        mod = part2.start % 8
        if mod > 0:
            part1.end -= mod
            part2.start = part1.end + 1

        part2.end = part2.start + self.SECTOR_NUM - 1

        return [part1, part2]
