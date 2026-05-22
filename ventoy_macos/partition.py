"""Disk partition."""

from attr import attr, hasattrs

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
        if not self.start and self.end:
            return

        return self.end - self.start + 1
