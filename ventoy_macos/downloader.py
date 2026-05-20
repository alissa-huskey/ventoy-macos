"""Ventoy download."""

import json
import subprocess
import urllib.request
from pathlib import Path
from shutil import copy

from ventoy_macos import VentoyMacosError
from ventoy_macos.common import require, run

REPO = "ventoy/Ventoy"

bp = breakpoint


def get_latest() -> str:
    """Return the git tag name for the latest ventoy release. """

    url = f"https://api.github.com/repos/{REPO}/releases/latest"
    req = urllib.request.Request(url, headers={"User-Agent": "ventoy-macos-install"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
    tag = data["tag_name"].lstrip("v")
    return tag


def download(version: str, workdir: str) -> str:
    """Download the ventoy release return the tarball path.

    Arguments:
        version (str): version to download
        workdir (str): path to download the tarball to
    """
    tarball = f"ventoy-{version}-linux.tar.gz"
    url = f"https://github.com/{REPO}/releases/download/v{version}/{tarball}"

    dest = Path(workdir) / tarball

    if not dest.is_file():
        urllib.request.urlretrieve(url, str(dest))

    return str(dest)


def extract(tarball: str, workdir: str) -> str:
    """Extract `tarball` to `workdir` and return the extracted Ventoy directory path."""
    # extract the tarball
    run(["tar", "xzf", tarball, "-C", workdir])

    path = Path(workdir)

    if not path.is_dir():
        raise VentoyMacosError(f"Not a valid directory: '{path}'")

    # find the extracted directory
    for entry in path.iterdir():
        if entry.name.startswith("ventoy-") and entry.is_dir():
            return str(entry)

    # raise if not found
    raise VentoyMacosError("Could not find extracted Ventoy directory")


def decompress(ventoy_dir: str, workdir: str):
    """Decompress ventoy images.

    Arguments:
        ventoy_dir (str): Path to extracted ventoy directory
        workdir (str): Destination path to decompress the images to

    Returns:
        Paths to boot_img, core_img and disk_img
    """
    require("xzcat")

    ventoy_dir = Path(ventoy_dir)
    workdir = Path(workdir)

    if not ventoy_dir.is_dir():
        raise VentoyMacosError(f"No such ventoy directory: '{ventoy_dir}'")

    if not workdir.is_dir():
        raise VentoyMacosError(f"No such destination directory: '{workdir}'")

    sources = [
        ("boot", "boot.img"),
        ("boot", "core.img.xz"),
        ("ventoy", "ventoy.disk.img.xz"),
    ]

    compressed = [Path(ventoy_dir, *parts) for parts in sources]

    for path in compressed:
        if not path.is_file():
            raise VentoyMacosError(f"Missing file: '{path}'")

    decompressed = []
    for path in compressed:
        dest = workdir / path.name.removesuffix(".xz")
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

    return decompressed
