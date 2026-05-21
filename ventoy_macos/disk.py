"""Disk operations."""

from functools import cached_property
from pathlib import Path
from re import compile as re_compile

from ventoy_macos import SECTOR_SIZE as _SECTOR_SIZE
from ventoy_macos import VentoyMacosError
from ventoy_macos.common import run
from ventoy_macos.object import Object

bp = breakpoint


class Disk(Object):
    """A disk object."""

    SECTOR_NUM = 65536  # 32MB for EFI partition
    SECTOR_SIZE = _SECTOR_SIZE
    SIZE_RE = re_compile(r'\((\d+) Bytes\)')

    _sectors = None

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
            self.info.get("removable media", "").lower() == "removable" and
            self.info.get("device location", "").lower() == "external"
        )

    @cached_property
    def info(self) -> dict:
        """Return the diskutil info."""
        if not self.exists():
            return

        def _tr_key(key):
            """Transform the key string."""
            return key.lower().strip()

        def _tr_value(value):
            """Transform the value string."""
            value = value.strip()
            translations = {"Yes": True, "No": False}
            return translations.get(value, value)

        result = run(["diskutil", "info", self.device])
        output = result.stdout

        lines = [line.strip().split(":") for line in output.splitlines() if line]
        data = {_tr_key(key): _tr_value(value) for key, value in lines}

        apfs = data.pop("this disk is an apfs container.  apfs information", False)

        if apfs == "":
            apfs = True

        data["is apfs container"] = apfs

        return data

    @property
    def sectors(self) -> int:
        """Return the disk size in 512-byte-units."""
        if not self._sectors:
            if "disk size" not in self.info:
                raise VentoyMacosError(f"Could not determine size of {self.device}")

            match = self.SIZE_RE.search(self.info["disk size"])

            if not match:
                raise VentoyMacosError(f"Could not determine size of {self.device}")

            total_bytes = int(match.group(1))
            self._sectors = total_bytes // self.SECTOR_SIZE
        return self._sectors

    @sectors.setter
    def sectors(self, value):
        """Set self.sectors."""
        self._sectors = value

    def to_gb(self, sectors) -> float:
        """Calculate GB size from sectors."""
        return (sectors * self.SECTOR_SIZE) / (1024**3)

    @property
    def gb(self) -> float:
        """Return the disk size in GB."""
        return self.to_gb(self.sectors)

    @property
    def current_layout(self):
        """Return the current partition layout."""
        result = run(["diskutil", "list", self.device])
        return result.stdout

    @cached_property
    def planned_layout(self):
        """Calculate Ventoy-compatible partition layout."""
        part1_start = 2048  # 1MB - Ventoy requirement
        part1_end = self.sectors - self.SECTOR_NUM - 34

        part2_start = part1_end + 1
        mod = part2_start % 8
        if mod > 0:
            part1_end -= mod
            part2_start = part1_end + 1

        part2_end = part2_start + self.SECTOR_NUM - 1

        return {
            "part1_start": part1_start,
            "part1_end": part1_end,
            "part1_sectors": part1_end - part1_start + 1,
            "part2_start": part2_start,
            "part2_end": part2_end,
            "part2_sectors": part2_end - part2_start + 1,
        }

    def verify(self) -> bool:
        """Verify the partition 1 offset."""
        return self.info and "offset" in self.info and self.info["offset"] == "2048"

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
