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
    return b2g(s2b(sectors))


def b2g(size: int) -> float:
    """Convert bytes to GB."""
    return size / (1024**3)


def g2b(gb: int) -> int:
    """Convert GB to bytes."""
    return gb * (1024**3)


def g2s(gb: int) -> int:
    """Convert GB to sectors."""
    return g2b(gb) // SECTOR_SIZE


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


def clear(size: int, prefix: bytes = b"") -> bytes:
    r"""Return a sequence of zero bytes to clear out a certain amount of space.

    Arguments:
        - size (int): size of space in bytes
        - prefix (bytes, default=b""): data to prepend to prepend (and subtract
            its length from zeros length)
    """
    empty = b"\x00" * (size - len(prefix))
    return prefix + empty
