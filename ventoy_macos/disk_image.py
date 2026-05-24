"""Contains the DiskImage class."""

import subprocess
from pathlib import Path
from shutil import copy

from attr import attr, hasattrs

from ventoy_macos import VentoyMacosError
from ventoy_macos.file import File
from ventoy_macos.object import Object

bp = breakpoint


@hasattrs
class DiskImage(Object):
    """Represents a disk image."""

    ATTRS = {
        "name": None,
        "relpath": tuple(),
        "source_dir": None,
        "dest_dir": None,
    }

    @property
    def id(self) -> str:
        """Return the identifer string for this image."""
        if not self.name:
            return
        return f"{self.name}_img"

    @attr
    def source(self) -> File:
        """Get the source File."""
        if not self._source and (self.source_dir and self.relpath):
            self._source = File(Path(self.source_dir, *self.relpath))
        return self._source

    @source.setter
    def source(self, value):
        """Set the source File."""
        if not value:
            return
        if not isinstance(value, File):
            value = File(Path(value))
        self._source = value

    @attr
    def dest(self) -> File:
        """Get the dest File."""
        if not self._dest and (self.dest_dir and self.relpath):
            name = self.relpath[-1].removesuffix(".xz")
            self._dest = File(Path(self.dest_dir, name))
        return self._dest

    @dest.setter
    def dest(self, value):
        """Set the dest File."""
        if not value:
            return
        if not isinstance(value, File):
            value = File(Path(value))
        self._dest = value

    @property
    def size(self) -> int:
        """Return the size of the destination file."""
        return self.dest and self.dest.size

    @property
    def data(self) -> bytes:
        """Read the image file."""
        return self.dest and self.dest.data

    def decompress(self):
        """Decompress ventoy images."""
        if not self.source.exists():
            raise VentoyMacosError(
                f"Disk image source file not found: '{self.source.path}'"
            )

        #  if the source image is not compressed, just copy it
        if self.source.path.suffix == ".img":
            copy(self.source.path, self.dest.path)
            return

        if self.dest.exists():
            return

        # decompress the file
        with open(self.dest.path, "wb") as out:
            result = subprocess.run(
                ["xzcat", (str(self.source.path))],
                stdout=out,
                timeout=60,
            )

            if result.returncode != 0:
                raise VentoyMacosError(
                    f"Failed to decompress '{self.source.path.name}'"
                )
