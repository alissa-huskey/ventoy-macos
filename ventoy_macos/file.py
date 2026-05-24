"""Contains the File class."""

from pathlib import Path

from attr import attr, hasattrs

from ventoy_macos.object import Object

bp = breakpoint


@hasattrs
class File(Object):
    """Represents a file on the filesystem."""

    def __init__(self, path: Path = None, **kwargs):
        """Initialize the object."""
        self.path = path
        super().__init__(**kwargs)

    def exists(self) -> bool:
        """Return True if the file exists and is a file."""
        return bool(self.path and self.path.is_file())

    @property
    def size(self) -> int:
        """Return the file size in bytes."""
        if not self.exists():
            return
        return self.path.stat().st_size

    def read(self) -> bytes:
        """Read the image file."""
        if not self.exists():
            return
        self._data = self.path.read_bytes()
        return self._data

    @attr
    def data(self) -> bytes:
        """Return the contents of the file in bytes."""
        if self.exists() and not self._data:
            self.read()
        return self._data
