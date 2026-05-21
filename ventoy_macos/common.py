"""Common untility functions."""

import subprocess

from ventoy_macos import SECTOR_SIZE, VentoyMacosError


def run(cmd, check=True, capture=True, timeout=30):
    """Run a command on the CLI."""
    result = subprocess.run(cmd, capture_output=capture, text=True, timeout=timeout)
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
