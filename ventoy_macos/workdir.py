"""Logic related to the working directory."""

import tempfile
from os import chmod
from pathlib import Path
from re import compile as re_compile
from stat import S_IMODE

import requests
from attr import attr, hasattrs

from ventoy_macos import VentoyMacosError
from ventoy_macos.common import run
from ventoy_macos.disk_image import DiskImage
from ventoy_macos.object import Object

bp = breakpoint


@hasattrs
class Workdir(Object):
    """Represents the working directory.

    Logic for the local working directory and its contents. Handles downloading
    and extracting Ventoy.
    """

    VERSION_MATCHER = re_compile(r"^\d+[.]\d+[.]\d+")

    IMAGES_RELDIRS = {
        "boot": ("boot", "boot.img"),
        "core": ("boot", "core.img.xz"),
        "disk": ("ventoy", "ventoy.disk.img.xz"),
    }

    REPO = "ventoy/Ventoy"

    PREFIX = "ventoy-macos-"

    RW = 0o66   # go+rw
    RWX = 0o77  # go+rwx

    ATTRS = {
        "path": None,
        "version": None,
        "images": {},
    }

    TMPDIR = None

    def __init__(self, base: Path = None, mktemp: bool = False, **kwargs):
        """Initialize."""
        super().__init__(base=base, **kwargs)

        if mktemp:
            self.mktemp()

    def __str__(self):
        """Return the human readable path."""
        if not self.path:
            return super().__str__()
        else:
            return str(self.path)

    @attr
    def images(self) -> list:
        """Return a mapping of DiskImage objects."""
        if (
            (self._images is None) and
            self.path and self.ventoy_dir
        ):
            self._images = {
                f"{name}_img": DiskImage(
                    name=name,
                    relpath=relpath,
                    source_dir=self.ventoy_dir,
                    dest_dir=self.path,
                )
                for name, relpath in self.IMAGES_RELDIRS.items()
            }
        return self._images

    @attr(method="setter")
    def base(self, value):
        """Return the path to the base working dir."""
        if not value:
            return
        if not isinstance(value, Path):
            value = Path(value)

        # detect if the value is actually the path, not the base path
        # (points to a version named directory like "1.1.12")
        if self.VERSION_MATCHER.match(value.name):
            self._base = value.parent
            self.version = value.name
            return

        self._base = value

    @attr
    def path(self) -> Path:
        """Return the path to the directory for this version in the working dir."""
        if (not self._path) and self.base and self.version:
            self._path = self.base / self.version
        return self._path

    @classmethod
    def get_latest(cls) -> str:
        """Return the git tag name for the latest ventoy release."""
        url = f"https://api.github.com/repos/{cls.REPO}/releases/latest"
        response = cls.request(url)
        data = response.json()

        return data["tag_name"].lstrip("v")

    def has_images(self) -> bool:
        """Return True if the path contains the decompressed disk images."""
        return all([i.dest.exists() for i in self.images.values()])

    @classmethod
    def request(self, url, *args, **kwargs) -> requests.Response:
        """Make a get request."""
        response = requests.get(url, *args, **kwargs)

        if not response.ok:
            raise VentoyMacosError(
                f"Request Failed [{response.status_code} {response.reason}]: {url}",
                response=response
            )

        return response

    @property
    def tarball_path(self):
        """Return the path to the tarball in the working directory."""
        if not self.path and self.version:
            return
        return self.path / f"ventoy-{self.version}-linux.tar.gz"

    @property
    def ventoy_dir(self):
        """Return the path to the ventoy-x-x-xx subdir."""
        if not self.path and self.version:
            return
        return self.path / f"ventoy-{self.version}"

    @property
    def url(self) -> str:
        """Return the URL for downloading the ventoy tarball."""
        return (
            f"https://github.com/{self.REPO}/releases/download/"
            f"v{self.version}/{self.tarball_path.name}"
        )

    def find_ventoy_dir(self, version: str = None) -> Path:
        """Look for an extracted ventoy dir in path and return the Path.

        Arguments:
            version (str, optional): restrict to this version if present
        """
        if not (self.path and self.path.is_dir()):
            return False

        pattern = "ventoy-*"
        if version:
            pattern = f"{pattern[:-1]}{version}"

        for path in self.path.glob(pattern):
            if path.is_dir():
                return path

        return False

    def download(self) -> Path:
        """Download the ventoy release return the tarball path."""
        dest = self.tarball_path

        if not dest.is_file():
            response = self.request(self.url)
            dest.write_bytes(response.content)

            return response

    def extract(self) -> Path:
        """Extract `tarball` to `path` and set .ventoy_dir."""
        # check to see if the directory already exists first
        if (path := self.find_ventoy_dir(self.version)):
            return path

        # extract the tarball
        run(["tar", "xzf", str(self.tarball_path), "-C", str(self.path)])

        if not self.path.is_dir():
            raise VentoyMacosError(f"Not a valid directory: '{self.path}'")

        # find the extracted directory
        if (path := self.find_ventoy_dir(self.version)):
            return path

        # raise if not found
        raise VentoyMacosError("Could not find extracted Ventoy directory")

    def decompress(self):
        """Decompress disk images."""
        for img in self.images.values():
            img.decompress()

    def chmod(self, path: Path = None):
        """Add write permissions to directory and all children recursively."""
        path = path or self.base

        if not (path and path.exists()):
            raise VentoyMacosError("Cannot chmod. Nothing exists at path: {path}")

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

    def mktemp(self):
        """Create a tmp base working dir if base is not set."""
        if not self.base:
            self.base = tempfile.mkdtemp(
                prefix="ventoy-macos-",
                dir=self.TMPDIR,
            )

    def mkdirs(self):
        """Create working directory and children."""
        self.mktemp()
        (self.path / "data").mkdir(parents=True, exist_ok=True)
