"""Contains the App class."""

from argparse import Namespace
from functools import cached_property
from pathlib import Path

from attr import attr, hasattrs

from ventoy_macos.builder import Builder
from ventoy_macos.disk import Disk
from ventoy_macos.gpt import GPT
from ventoy_macos.logger import Logger
from ventoy_macos.object import Object
from ventoy_macos.workdir import Workdir

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

    ATTRS = {
        "args": None,
    }

    def __init__(self, args: Namespace = None, mktemp: bool = True, **kwargs):
        """Initialize object."""
        self.args = args
        self.mktemp = mktemp
        super().__init__(**kwargs)

    @cached_property
    def log(self) -> Logger:
        """Return a Logger instance."""
        return Logger(path=self.workdir.path / "ventoy-macos.log")

    @attr
    def workdir(self) -> Path:
        """Return the directory to save and extract working files from."""
        if not self._workdir:
            self._workdir = Workdir(
                (self.args and self.args.dir or None),
                version=self.version,
                mktemp=self.mktemp,
            )
        return self._workdir

    @attr
    def gpt(self) -> GPT:
        """Return a GPT object."""
        if not self.disk:
            return

        if not self._gpt:
            self._gpt = GPT(self.disk.sectors, self.disk.planned_layout)
        return self._gpt

    @attr
    def builder(self) -> Builder:
        """Return the GPT Builder object."""
        if self.disk and not self._builder:
            self._builder = Builder(
                self.disk,
                gpt=self.gpt,
                images=self.workdir.images,
                path=self.workdir.path,
            )
        return self._builder

    @attr(method="getter")
    def disk(self) -> Disk:
        """Get the disk attribute."""
        if not self._disk and self.args:
            self._disk = Disk(self.args.disk)

        return self._disk

    @attr(method="getter")
    def version(self) -> str:
        """Get the version attribute."""
        if not self._version:
            if self.args and self.args.ventoy_version:
                self._version = self.args.ventoy_version
        return self._version
