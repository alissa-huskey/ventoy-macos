"""CLI."""

import argparse
import sys


def err(*msg):
    """Print an error message to stderr."""
    print(f"\n\033[31mERROR\033[0m:", *msg, file=sys.stderr)


def die(*msg):
    """Print an error message and exit."""
    err(*msg)
    sys.exit(1)


def confirm(msg):
    """Prompt with a question and quit unless the answer is 'y'."""
    answer = input(f"\n{msg} (y/N): ").strip().lower()
    if answer != "y":
        print("Aborted.")
        sys.exit(0)

    return True


def parse_args():
    parser = argparse.ArgumentParser(
        description="Install Ventoy on a USB drive from macOS.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    sudo python3 ventoy-macos-install.py /dev/disk4
    sudo python3 ventoy-macos-install.py /dev/disk4 --ventoy-version 1.1.10
    sudo python3 ventoy-macos-install.py /dev/disk4 --exfat
        """,
    )
    parser.add_argument("disk", help="Target disk device (e.g., /dev/disk4)")
    parser.add_argument(
        "--exfat",
        action="store_const",
        const="exfat",
        dest="fs_type",
        default="exfat",
        help="Format data partition as exFAT (default)",
    )
    parser.add_argument(
        "--ventoy-version",
        default=None,
        help="Ventoy version to install (default: latest)",
    )
    parser.add_argument(
        "--work-dir",
        default=None,
        help="Working directory for downloads (default: temp directory)",
    )

    args = parser.parse_args()

    return args
