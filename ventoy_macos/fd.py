"""File descriptor IO logic."""

import os

from ventoy_macos.disk import Disk
from ventoy_macos.object import Object


class FD(Object):
    """File descriptor."""

    def __init__(self, disk: Disk = None):
        """Initialize the object."""
        self.disk = disk
        self.id = None
        self.is_open = False

    def open(self):
        """Open the device for writing.

        Returns `self`, which allows it to be used as a context manager.
        """
        self.id = os.open(self.disk.raw_device, os.O_RDWR)
        self.is_open = True
        return self

    def close(self):
        """Close the device."""
        os.close(self.id)
        self.is_open = False

    def seek(self, position):
        """Set the position of the file descriptor and return the new position."""
        return os.lseek(self.id, position, os.SEEK_SET)

    def _write(self, data):
        """Write a bytes object to the file descriptor at the current position."""
        os.write(self.id, data)

    def write(self, position, data):
        """Set the position and write data to the file descriptor."""
        self.seek(position)
        self._write(data)

    def save(self):
        """Force write of fd to disk."""
        os.fsync(self.id)

    def _read(self, length: int) -> bytes:
        """Read from the file descriptor from current position."""
        return os.read(self.id, length)

    def read(self, position: int, length: int) -> bytes:
        """Set the position then read from the file descriptor."""
        self.seek(position)
        return self._read(length)

    def patch(self, sector_num, offset, data):
        """Read-modify-write a sector to patch sub-sector bytes."""
        sector_start = sector_num * Disk.SECTOR_SIZE
        contents = bytearray(self.read(sector_start, Disk.SECTOR_SIZE))
        contents[offset: offset + len(data)] = data
        self.write(sector_start, bytes(contents))

    def __enter__(self, *args, **kwargs):
        """Open the file descriptor."""
        return self.open(*args, **kwargs)

    def __exit__(self, *args):
        """Close the file descriptor."""
        self.close()
        return False
