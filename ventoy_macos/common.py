"""Common untility functions."""

import subprocess

from ventoy_macos import SECTOR_SIZE, VentoyMacosError

bp = breakpoint


def run(cmd, check=True, capture=True, text=True, timeout=30):
    """Run a command on the CLI."""
    result = subprocess.run(cmd, capture_output=capture, text=text, timeout=timeout)
    if check and result.returncode != 0:
        stderr = result.stderr if capture else ""
        raise VentoyMacosError(f"Command failed: {' '.join(cmd)}\n{stderr}")
    return result


def b2s(_bytes: int) -> tuple:
    """Convert bytes to (sectors, offset)."""
    return (_bytes // SECTOR_SIZE, _bytes % SECTOR_SIZE)


def s2b(sectors: int) -> int:
    """Convert sectors to bytes."""
    return sectors * SECTOR_SIZE


def s2g(sectors: int) -> float:
    """Convert sectors to GB."""
    return (sectors * SECTOR_SIZE) / (1024**3)


def s2m(sectors: int) -> float:
    """Convert sectors to MB."""
    return s2g(sectors) * 1000


def size_text(sectors: int) -> str:
    """Return size human readable string (MiB or GiB)."""
    value = s2g(sectors)
    prec = 1
    units = "GiB"

    if value < 1:
        value = s2m(sectors)
        prec = 0
        units = "MiB"

    return f"{value:.{prec}f} {units}"
