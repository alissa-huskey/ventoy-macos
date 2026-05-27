"""Disk partition."""

from functools import cached_property

from attr import attr, hasattrs

from ventoy_macos.device import Device

bp = breakpoint


@hasattrs
class Partition(Device):
    """Disk partition."""

    ATTRS = {
        "number": None,
        "size": None,
        "start": None,
        "end": None,
        "parent": None,
    }

    @attr
    def sectors(self):
        """Return the number of sectors in this partition."""
        if not self._sectors:
            if self.start and self.end:
                self._sectors = self.end - self.start + 1
            elif self.size:
                self._sectors = super().sectors
        return self._sectors

    @cached_property
    def offset(self) -> int:
        """Return the partition offset position."""
        return self.info_get("PartitionMapPartitionOffset")
