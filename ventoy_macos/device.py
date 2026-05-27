"""A device."""

import plistlib
import subprocess
from functools import cached_property
from pathlib import Path

from attr import attr, hasattrs

from ventoy_macos.common import b2g, b2s, run
from ventoy_macos.object import Object

bp = breakpoint


@hasattrs
class Device(Object):
    """Represents a device."""

    def __init__(self, location: str = None, **kwargs):
        """Initialize."""
        self.location = location
        super().__init__(**kwargs)

    def __str__(self):
        """Return a human readable string."""
        klass = self.__class__.name
        location = self.location or ""
        return f"{klass}({location})"

    @cached_property
    def id(self) -> bool:
        """Return the disk identifier."""
        if not self.location:
            return
        return self.location.removeprefix("/dev/")

    def info_get(self, *keys, default=None):
        """Return the first non-empty value from info matching any key from keys."""
        if self.info is None:
            return
        for key in keys:
            if (value := self.info.get(key)) not in (None, ""):
                return value
        return default

    @cached_property
    def name(self) -> str:
        """Return the volume name."""
        name = self.info_get(
            "MediaName",
            "IORegistryEntryName",
            "VolumeName",
        )
        return name or ""

    def is_external(self) -> bool:
        """Return True if the disk is external."""
        is_internal = self.info_get("Internal", "OSInternalMedia")
        is_removable = self.info_get(
            "RemovableMedia",
            "Removable",
            "RemovableMediaOrExternalDevice",
        )

        return (is_removable and not is_internal)

    @cached_property
    def scheme(self) -> str:
        """Return the partition table scheme."""
        return self.info_get("Content") or ""

    @attr
    def size(self) -> int:
        """Return the disk size in bytes."""
        if not self._size and self.info:
            self._size = self.info_get("TotalSize", "Size")
        return self._size

    @cached_property
    def free(self) -> int:
        """Return the amount of free space in bytes."""
        return self.info.get("FreeSpace")

    def exists(self) -> bool:
        """Return True if the disk exists."""
        return self.location and Path(self.location).exists()

    @attr
    def info(self) -> dict:
        """Return the diskutil info data."""
        if self._info is None and self.exists():
            raw = subprocess.check_output(["diskutil", "info", "-plist", self.location])
            self._info = plistlib.loads(raw)

        return self._info or {}

    def is_partition(self) -> bool:
        """Return True if the device is a partition."""
        is_partition = self.info_get("PartitionMapPartition")
        is_whole = self.info_get("WholeDisk")
        return (is_partition and not is_whole)

    def mount(self):
        """Mount the disk."""
        run(["diskutil", "mountDisk", self.location], check=False)

    def unmount(self):
        """Mount the disk."""
        run(["diskutil", "unmountDisk", "force", self.location], check=False)

    def format(self):
        """Format the disk."""
        result = run(["newfs_exfat", "-v", "Ventoy", self.location], check=False)
        if result.returncode != 0:
            result = run(["diskutil", "eraseVolume", "ExFAT", "Ventoy", self.location])
        return result.returncode == 0

    @attr
    def sectors(self) -> int:
        """Return the disk size in 512-byte-units."""
        if not self._sectors and self.size:
            self._sectors, _ = b2s(self.size)
        return self._sectors

    @property
    def gb(self) -> float:
        """Return the disk size in GB."""
        return b2g(self.size)

    @cached_property
    def fs(self) -> str:
        """Return the filesystem."""
        long = self.info_get("Content")
        short = self.info_get(
            "FilesystemUserVisibleName",
            "FilesystemName",
            "FilesystemType",
        )
        if long and short:
            return f"{short} ({long})"
        elif long:
            return long
        elif short:
            return short
        else:
            return ""
