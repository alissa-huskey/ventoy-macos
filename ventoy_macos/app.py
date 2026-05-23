"""Contains the App class."""

import json
import subprocess
import tempfile
import urllib.request
from argparse import Namespace
from pathlib import Path
from shutil import copy

from attr import attr, hasattrs

from ventoy_macos import VentoyMacosError
from ventoy_macos.common import run
from ventoy_macos.disk import Disk
from ventoy_macos.gpt import build_gpt
from ventoy_macos.object import Object

bp = breakpoint


@hasattrs
class App(Object):
    """Contains the data and most of the application logic functions.

    (Except for anything that involves the UX or is in a more specialized
    class.)
    """

    REPO = "ventoy/Ventoy"

    args = None

    def __init__(self, args: Namespace = None, **kwargs):
        """Initialize object."""
        self.args = args
        super().__init__(**kwargs)

    @attr
    def workdir(self) -> Path:
        """Return the directory to save and extract working files from."""
        if not self._workdir:
            if self.args and self.args.work_dir:
                workdir = Path(self.args.work_dir)
                workdir.mkdir(exist_ok=True)
            else:
                workdir = tempfile.mkdtemp(prefix="ventoy-macos-")
                workdir = Path(workdir)
            self._workdir = workdir
        return self._workdir

    @workdir.setter
    def workdir(self, value):
        """Set the directory to save and extract working files from."""
        self._workdir = Path(value)

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
            else:
                self.version = self.get_latest()
        return self._version

    def get_ventoy(self):
        """Download and extract Ventoy."""
        self.download()
        self.extract()
        self.decompress()

    def build_gpt(self):
        """Build the GPT partition table."""
        objects = build_gpt(self.disk.sectors, self.disk.planned_layout)
        self.mbr, self.primary, self.entries, self.backup = objects

    def get_latest(self) -> str:
        """Return the git tag name for the latest ventoy release."""
        url = f"https://api.github.com/repos/{self.REPO}/releases/latest"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "ventoy-macos-install"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        tag = data["tag_name"].lstrip("v")
        return tag

    def download(self) -> Path:
        """Download the ventoy release return the tarball path."""
        tarball = f"ventoy-{self.version}-linux.tar.gz"
        url = (
            f"https://github.com/{self.REPO}/releases/download/"
            f"v{self.version}/{tarball}"
        )

        dest = Path(self.workdir) / tarball

        if not dest.is_file():
            urllib.request.urlretrieve(url, str(dest))

        self.tarball = dest
        return self.tarball

    def extract(self) -> Path:
        """Extract `tarball` to `workdir` and set .ventoy_dir."""
        # extract the tarball
        run(["tar", "xzf", self.tarball, "-C", self.workdir])

        if not self.workdir.is_dir():
            raise VentoyMacosError(f"Not a valid directory: '{self.workdir}'")

        # find the extracted directory
        for entry in self.workdir.iterdir():
            if entry.name.startswith("ventoy-") and entry.is_dir():
                self.ventoy_dir = entry
                return self.ventoy_dir

        # raise if not found
        raise VentoyMacosError("Could not find extracted Ventoy directory")

    def decompress(self):
        """Decompress ventoy images.

        Arguments:
            ventoy_dir (str): Path to extracted ventoy directory
            workdir (str): Destination path to decompress the images to

        Returns:
            Paths to boot_img, core_img and disk_img
        """
        if not self.ventoy_dir.is_dir():
            raise VentoyMacosError(f"No such ventoy directory: '{self.ventoy_dir}'")

        if not self.workdir.is_dir():
            raise VentoyMacosError(f"No such destination directory: '{self.workdir}'")

        sources = [
            ("boot", "boot.img"),
            ("boot", "core.img.xz"),
            ("ventoy", "ventoy.disk.img.xz"),
        ]

        compressed = [Path(self.ventoy_dir, *parts) for parts in sources]

        for path in compressed:
            if not path.is_file():
                raise VentoyMacosError(f"Missing file: '{path}'")

        decompressed = []
        for path in compressed:
            dest = self.workdir / path.name.removesuffix(".xz")
            decompressed.append(dest)

            # if the source image is not compressed, just copy it
            if path.suffix == ".img":
                copy(path, dest)
                continue

            if not dest.is_file():
                # decompress the file
                with open(dest, "wb") as out:
                    result = subprocess.run(["xzcat", path], stdout=out, timeout=60)
                    if result.returncode != 0:
                        raise VentoyMacosError(f"Failed to decompress '{path.name}'")

        self.boot_img, self.core_img, self.disk_img = decompressed
