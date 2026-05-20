"""CLI."""

import argparse
import os
import sys
import tempfile
import time
import uuid

from ventoy_macos.common import has
from ventoy_macos.disk import Disk
from ventoy_macos.downloader import decompress, download, extract, get_latest
from ventoy_macos.fd import FD
from ventoy_macos.gpt import build_gpt


def err(*msg):
    """Print an error message to stderr."""
    print("\n\033[31mERROR\033[0m:", *msg, file=sys.stderr)


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


def verify(device):
    """Print final disk layout and verify partition 1 offset."""
    disk = Disk(device)
    time.sleep(2)
    disk.mount()
    time.sleep(1)

    print("\n" + "=" * 50)
    print("Disk layout:")
    print("=" * 50)
    print(disk.current_layout)

    partition = Disk(f"{device}s1")
    if partition.verify():
        print("  -> Correct! Partition 1 starts at sector 2048 (1MB)")
    else:
        print("  -> WARNING: Partition 1 does not start at sector 2048!")


def parse_args():
    """Parse input arguments."""
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


def run():
    """Run the CLI."""
    args = parse_args()

    disk = Disk(args.disk)

    if os.geteuid() != 0:
        die(
            "This script must be run as root. "
            "Use: sudo python3 ventoy-macos-install.py ..."
        )

    if sys.platform != "darwin":
        die("This script is designed for macOS only.")

    # Check xz is available
    if not has("xzcat"):
        die("xz is required but not found. Install it with: brew install xz")

    # Validate disk
    if not disk.is_disk():
        die(f"Invalid disk device: {disk}")

    if disk.is_system_disk():
        die("Refusing to operate on disk0/disk1 (likely your system disk).")

    # Get disk info
    print(f"Target disk: {disk.device}")
    print(f"Disk size: {disk.gb:.1f} GiB ({disk.sectors} sectors)")

    # Show current layout
    print("\nCurrent layout:")
    print(disk.current_layout)

    # Calculate partition layout
    layout = disk.planned_layout
    p1_gb = disk.to_gb(layout["part1_sectors"])
    p2_mb = disk.to_gb(layout["part2_sectors"])

    print("\nPlanned Ventoy layout:")
    print((
        f"  Part 1 (Ventoy, exFAT):  {p1_gb:.1f} GiB  "
        "[sectors {layout['part1_start']}-{layout['part1_end']}]"
    ))
    print((
        f"  Part 2 (VTOYEFI, FAT16): {p2_mb:.0f} MiB   "
        "[sectors {layout['part2_start']}-{layout['part2_end']}]"
    ))

    confirm("ALL DATA ON THIS DISK WILL BE DESTROYED. Continue?")

    # Setup working directory
    if args.work_dir:
        workdir = args.work_dir
        os.makedirs(workdir, exist_ok=True)
    else:
        workdir = tempfile.mkdtemp(prefix="ventoy-macos-")

    print(f"\nWorking directory: {workdir}")

    # Get Ventoy version
    version = args.ventoy_version or get_latest()
    print(f"Ventoy version: {version}")

    # Download and extract
    tarball = download(version, workdir)
    ventoy_dir = extract(tarball, workdir)
    boot_img, core_img, disk_img = decompress(ventoy_dir, workdir)

    print("\nBoot images ready:")
    print(f"  boot.img:         {os.path.getsize(boot_img)} bytes")
    print(f"  core.img:         {os.path.getsize(core_img)} bytes")
    print(f"  ventoy.disk.img:  {os.path.getsize(disk_img)} bytes")

    # Build GPT
    print("\nBuilding GPT partition table...")
    mbr, primary, entries, backup = build_gpt(disk.sectors, layout)

    # Final confirmation
    confirm("Ready to write. This is your last chance to abort. Proceed?")

    # Write everything
    write_to_disk(
        disk.raw_device,
        disk.device,
        disk.sectors,
        disk.planned_layout,
        mbr,
        primary,
        entries,
        backup,
        boot_img,
        core_img,
        disk_img,
    )

    # Format partition 1
    format_partition1(disk, args.fs_type)

    # Verify
    verify(disk)

    print(f"\n{'=' * 50}")
    print(f"Ventoy {version} installed successfully!")
    print(f"{'=' * 50}")
    print("\nYou can now copy ISO/WIM/IMG/VHD files to the 'Ventoy' partition.")
    print("Boot from the USB drive and Ventoy will list all bootable images.")


def format_partition1(disk, fs_type="exfat"):
    """Format partition 1 with the specified filesystem."""
    device = f"{disk}s1"
    partition = Disk(device)

    print("\nWaiting for macOS to detect partitions...")
    time.sleep(3)

    partition.unmount()
    time.sleep(1)

    if fs_type != "exfat":
        print(f"Formatting {device} as exFAT...")
    else:
        # NTFS is not natively supported for formatting on macOS
        # but Ventoy data partition can remain unformatted and be formatted elsewhere
        print("Warning: macOS cannot natively format NTFS.")
        print(
            f"Formatting {device} as exFAT instead "
            "(readable on Windows/Linux/macOS)."
        )

    partition.format()


def write_to_disk(
    raw_device,
    device,
    disk_sectors,
    layout,
    mbr,
    primary,
    entries,
    backup,
    boot_img_path,
    core_img_path,
    disk_img_path,
):
    """Write GPT and Ventoy boot code to the disk."""
    boot_img = open(boot_img_path, "rb").read()
    core_img = open(core_img_path, "rb").read()
    disk_img = open(disk_img_path, "rb").read()

    disk = Disk(device)

    # Unmount
    print("Unmounting disk...")
    disk.unmount()
    time.sleep(2)

    print("Writing to disk...")
    fd = FD(disk)
    fd.open()

    try:
        # Zero first 1MB (protective MBR + GPT header + entries area)
        print("  Zeroing first 1MB...")
        fd.write(0, b"\x00" * (2048 * Disk.SECTOR_SIZE))

        # Zero backup GPT area
        print("  Zeroing backup GPT area...")
        fd.write(
            (disk_sectors - 33) * Disk.SECTOR_SIZE,
            b"\x00" * (33 * Disk.SECTOR_SIZE)
        )

        # Write protective MBR
        print("  Writing protective MBR...")
        fd.write(0, mbr)

        # Write primary GPT header (sector 1)
        print("  Writing primary GPT header...")
        fd.write(Disk.SECTOR_SIZE, primary)

        # Write primary GPT entries (sectors 2-33)
        print("  Writing GPT entries...")
        fd.write(2 * Disk.SECTOR_SIZE, entries)

        # Write backup GPT entries + header
        print("  Writing backup GPT...")
        fd.write((disk_sectors - 33) * Disk.SECTOR_SIZE, entries)
        fd.write((disk_sectors - 1) * Disk.SECTOR_SIZE, backup)

        # Write Ventoy boot.img (446 bytes of BIOS boot code to MBR)
        print("  Writing Ventoy boot.img...")
        fd.patch(0, 0, boot_img[:446])

        # GPT marker at offset 92
        fd.patch(0, 92, b"\x22")

        # Write core.img to sectors 34-2047 (GPT gap area)
        print("  Writing core.img...")
        core = core_img[: 2014 * Disk.SECTOR_SIZE]
        if len(core) % Disk.SECTOR_SIZE:
            core += b"\x00" * (Disk.SECTOR_SIZE - len(core) % Disk.SECTOR_SIZE)
        fd.write(34 * Disk.SECTOR_SIZE, core)

        # Second GPT marker at offset 17908
        fd.patch(17908 // Disk.SECTOR_SIZE, 17908 % Disk.SECTOR_SIZE, b"\x23")

        # Write ventoy.disk.img to partition 2
        part2_start = layout["part2_start"]
        print(f"  Writing ventoy.disk.img at sector {part2_start}...")
        fd.write(part2_start * Disk.SECTOR_SIZE, disk_img)

        # Disk UUID at offset 384
        fd.patch(0, 384, uuid.uuid4().bytes)

        # Disk signature at offset 440
        fd.patch(0, 440, os.urandom(4))

        fd.save()
        print("  All writes complete.")
    finally:
        fd.close()
