"""Contains the App class."""

import tempfile
from argparse import Namespace
from functools import cached_property
from os import chmod
from pathlib import Path
from stat import S_IMODE

from attr import attr, hasattrs

from ventoy_macos.builder import Builder
from ventoy_macos.disk import Disk
from ventoy_macos.disk_image import DiskImage
from ventoy_macos.downloader import Downloader
from ventoy_macos.gpt import GPT
from ventoy_macos.logger import Logger
from ventoy_macos.object import Object

bp = breakpoint


@hasattrs
class App(Object):
    """Application logic.

    Responsible for keeping track of and interfacing between the top level
    objects and data.

    Contains the data and most of the application logic functions.

    (Except for anything that involves the UX or is in a more specialized
    class.)
    """

    REPO = "ventoy/Ventoy"

    RW = 0o66  # go+rw permissions
    RWX = 0o77

    IMAGES_RELDIRS = {
        "boot": ("boot", "boot.img"),
        "core": ("boot", "core.img.xz"),
        "disk": ("ventoy", "ventoy.disk.img.xz"),
    }

    ATTRS = {
        "args": None,
    }

    def __init__(self, args: Namespace = None, **kwargs):
        """Initialize object."""
        self.args = args
        super().__init__(**kwargs)

    @cached_property
    def log(self) -> Logger:
        """Return a Logger instance."""
        return Logger(path=self.workdir / "ventoy-macos.log")

    @attr
    def workdir(self) -> Path:
        """Return the directory to save and extract working files from."""
        if not self._workdir:
            if self.args and self.args.work_dir:
                workdir = self.args.work_dir
            else:
                workdir = tempfile.mkdtemp(prefix="ventoy-macos-")
            self._workdir = Path(workdir)
        (self._workdir / "data").mkdir(exist_ok=True)
        return self._workdir

    @workdir.setter
    def workdir(self, value):
        """Set the directory to save and extract working files from."""
        self._workdir = Path(value)

    @attr
    def gpt(self) -> GPT:
        """Return a GPT object."""
        if not self.disk:
            return

        if not self._gpt:
            self._gpt = GPT(self.disk.sectors, self.disk.planned_layout)
        return self._gpt

    @attr
    def downloader(self) -> Downloader:
        """Return a Downloader object."""
        if not self._downloader and (self.version and self.workdir):
            self._downloader = Downloader(
                version=self.version,
                workdir=self.workdir
            )
        return self._downloader

    @attr
    def builder(self) -> Builder:
        """Return the GPT Builder object."""
        if self.disk and not self._builder:
            self._builder = Builder(
                self.disk,
                gpt=self.gpt,
                images=self.images,
                path=self.workdir,
            )
        return self._builder

    @attr(method="getter")
    def disk(self) -> Disk:
        """Get the disk attribute."""
        if not self._disk and self.args:
            self._disk = Disk(self.args.disk)

        return self._disk

    @attr
    def images(self) -> list:
        """Return a mapping of DiskImage objects."""
        if (
            self.workdir and
            self.downloader and
            self.downloader.ventoy_dir and
            not self._images
        ):
            self._images = {
                f"{name}_img": DiskImage(
                    name=name,
                    relpath=relpath,
                    source_dir=self.downloader.ventoy_dir,
                    dest_dir=self.workdir,
                )
                for name, relpath in self.IMAGES_RELDIRS.items()
            }
        return self._images

    @attr(method="getter")
    def version(self) -> str:
        """Get the version attribute."""
        if not self._version:
            if self.args and self.args.ventoy_version:
                self._version = self.args.ventoy_version
        return self._version

    def chmod(self, path: Path = None):
        """Add write permissions to directory and all children recursively."""
        path = path or self.workdir

        # make always iterable
        paths = [path]

        if path.is_dir():
            # add files in dir to iterable
            paths += list(path.iterdir())

        for file in paths:
            # get the current mode
            current = S_IMODE(file.stat().st_mode)

            if file.is_dir():
                new = current | self.RWX
            else:
                new = current | self.RW

            # recursively chmod
            if file != path and file.is_dir():
                self.chmod(file)

            # system chmod (go+rw)
            chmod(file, new)
