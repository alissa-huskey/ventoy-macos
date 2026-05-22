"""Disk partition."""

from attr import attr, hasattrs

from ventoy_macos.common import b2s
from ventoy_macos.object import Object

bp = breakpoint


@hasattrs
class Partition(Object):
    """Disk partition."""

    ATTRS = {
        "number": None,
        "format": None,
        "size": None,
        "identifier": None,
        "start": None,
        "end": None,
    }

    @attr
    def sectors(self):
        """Return the number of sectors in this partition."""
        if not self._sectors:
            if self.start and self.end:
                self._sectors = self.end - self.start + 1
            elif self.bytes:
                self._sectors, _ = b2s(self.bytes)
        return self._sectors
