"""Logic for downloading and extracting Ventoy."""

from pathlib import Path

import requests

from ventoy_macos import VentoyMacosError
from ventoy_macos.common import run
from ventoy_macos.object import Object

bp = breakpoint


class Downloader(Object):
    """Logic for downloading and extracting Ventoy."""

    REPO = "ventoy/Ventoy"

    ATTRS = {
        "workdir": None,
        "version": None,
        "boot_img": None,   # these are bytes objects for now
        "core_img": None,
        "disk_img": None,
    }

    @property
    def tarball_path(self):
        """Return the path to the tarball in the working directory."""
        if not self.workdir and self.version:
            return
        return self.workdir / f"ventoy-{self.version}-linux.tar.gz"

    @property
    def ventoy_dir(self):
        """Return the path to the tarball in the working directory."""
        if not self.workdir and self.version:
            return
        return self.workdir / f"ventoy-{self.version}"

    @property
    def url(self) -> str:
        """Return the URL for downloading the ventoy tarball."""
        return (
            f"https://github.com/{self.REPO}/releases/download/"
            f"v{self.version}/{self.tarball_path.name}"
        )

    def find_ventoy_dir(self, version: str = None) -> Path:
        """Look for an extracted ventoy dir in workdir and return the Path.

        Arguments:
            version (str, optional): restrict to this version if present
        """
        if not (self.workdir and self.workdir.is_dir()):
            return False

        pattern = "ventoy-*"
        if version:
            pattern = f"{pattern[:-1]}{version}"

        for path in self.workdir.glob(pattern):
            if path.is_dir():
                return path

        return False

    def request(self, url, *args, **kwargs) -> requests.Response:
        """Make a get request."""
        response = requests.get(url, *args, **kwargs)

        if not response.ok:
            raise VentoyMacosError(
                f"Request Failed [{response.status_code} {response.reason}]: {url}",
                response=response
            )

        return response

    def get_latest(self) -> str:
        """Return the git tag name for the latest ventoy release."""
        url = f"https://api.github.com/repos/{self.REPO}/releases/latest"
        response = self.request(url)
        data = response.json()

        self.version = data["tag_name"].lstrip("v")
        return self.version

    def download(self) -> Path:
        """Download the ventoy release return the tarball path."""
        dest = Path(self.workdir) / self.tarball_path

        if not dest.is_file():
            response = self.request(self.url)
            dest.write_bytes(response.content)

            return response

    def extract(self) -> Path:
        """Extract `tarball` to `workdir` and set .ventoy_dir."""
        # check to see if the directory already exists first
        if (path := self.find_ventoy_dir(self.version)):
            return path

        # extract the tarball
        run(["tar", "xzf", str(self.tarball_path), "-C", str(self.workdir)])

        if not self.workdir.is_dir():
            raise VentoyMacosError(f"Not a valid directory: '{self.workdir}'")

        # find the extracted directory
        if (path := self.find_ventoy_dir(self.version)):
            return path

        # raise if not found
        raise VentoyMacosError("Could not find extracted Ventoy directory")
