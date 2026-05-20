"""Common untility functions."""

import subprocess

from ventoy_macos import VentoyMacosError


def has(cmd):
    """Return True if command is found on the CLI."""
    result = run(["command", "-v", cmd], check=False)
    return result.returncode == 0


def run(cmd, check=True, capture=True, timeout=30):
    """Run a command on the CLI."""
    result = subprocess.run(cmd, capture_output=capture, text=True, timeout=timeout)
    if check and result.returncode != 0:
        stderr = result.stderr if capture else ""
        raise VentoyMacosError(f"Command failed: {' '.join(cmd)}\n{stderr}")
    return result
