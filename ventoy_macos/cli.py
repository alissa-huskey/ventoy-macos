"""CLI."""

import argparse
import os
import sys
import time

from ventoy_macos.app import App
from ventoy_macos.builder import Builder
from ventoy_macos.common import run
from ventoy_macos.disk import Disk


class CLI():
    """Everything that prints or receives input from the user."""

    def err(self, *msg):
        """Print an error message to stderr."""
        print("\n\033[31mERROR\033[0m:", *msg, file=sys.stderr)

    def die(self, *msg):
        """Print an error message and exit."""
        self.err(*msg)
        sys.exit(1)

    def confirm(self, msg):
        """Prompt with a question and quit unless the answer is 'y'."""
        answer = input(f"\n{msg} (y/N): ").strip().lower()
        if answer != "y":
            print("Aborted.")
            sys.exit(0)

        return True

    def has(self, cmd):
        """Return True if command is found on the CLI."""
        result = run(["command", "-v", cmd], check=False)
        return result.returncode == 0

    def parse_args(self):
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
            "--ventoy-version",
            default=None,
            help="Ventoy version to install (default: latest)",
        )
        parser.add_argument(
            "--work-dir",
            default=None,
            help="Working directory for downloads (default: temp directory)",
        )

        self.args = parser.parse_args()

    def validate(self, disk):
        """Check system and disk requirements."""
        if os.geteuid() != 0:
            self.die(
                "This script must be run as root. "
                "Use: sudo python3 ventoy-macos-install.py ..."
            )

        if sys.platform != "darwin":
            self.die("This script is designed for macOS only.")

        # Check xz is available
        if not self.has("xzcat"):
            self.die("xz is required but not found. Install it with: brew install xz")

        # Validate disk
        if not disk.is_disk():
            self.die(f"Invalid disk device: {disk}")

        if disk.is_system_disk():
            self.die("Refusing to operate on disk0/disk1 (likely your system disk).")

    def show_disk_info(self):
        """Print the disk layout and other info."""
        # Get disk info
        print(f"Target disk: {self.disk.device}")
        print(f"Disk size: {self.disk.gb:.1f} GiB ({self.disk.sectors} sectors)")

        # Show current layout
        print("\nCurrent layout:")
        print(self.disk.current_layout)

        # Calculate partition layout
        layout = self.disk.planned_layout
        p1_gb = self.disk.to_gb(layout["part1_sectors"])
        p2_mb = self.disk.to_gb(layout["part2_sectors"])

        print("\nPlanned Ventoy layout:")
        print((
            f"  Part 1 (Ventoy, exFAT):  {p1_gb:.1f} GiB  "
            "[sectors {layout['part1_start']}-{layout['part1_end']}]"
        ))
        print((
            f"  Part 2 (VTOYEFI, FAT16): {p2_mb:.0f} MiB   "
            "[sectors {layout['part2_start']}-{layout['part2_end']}]"
        ))

        self.confirm("ALL DATA ON THIS DISK WILL BE DESTROYED. Continue?")

    def write_to_disk(self):
        """Write GPT and Ventoy boot code to the disk."""
        builder = Builder(
            self.app.disk,
            mbr=self.app.mbr,
            primary=self.app.primary,
            entries=self.app.entries,
            backup=self.app.backup,
            images_path=self.app.workdir,
        )

        print("Unmounting disk...")
        builder.unmount()

        print("Writing to disk...")

        with builder.fd.open():
            # (protective MBR + GPT header + entries area)
            print("  Zeroing first 1MB...")
            builder.write_init_header()

            print("  Zeroing backup GPT area...")
            builder.write_init_backup()

            print("  Writing protective MBR...")
            builder.write_mbr()

            # sector 1
            print("  Writing primary GPT header...")
            builder.write_primary_header()

            # sectors 2-33
            print("  Writing GPT entries...")
            builder.write_entries()

            # (+ header)
            print("  Writing backup GPT...")
            builder.write_backup()

            # 446 bytes of BIOS boot code to MBR
            print("  Writing Ventoy boot.img...")
            builder.write_boot_img()

            # GPT marker at offset 92
            builder.write_gpt_marker(92, b"\x22")

            # sectors 34-2047 (GPT gap area)
            print("  Writing core.img...")
            builder.write_core_img()

            # Second GPT marker at offset 17908
            builder.write_second_gpt_marker()

            print("  Writing ventoy.disk.img to partition 2...")
            builder.write_disk_img()

            # Disk UUID at offset 384
            builder.write_disk_uuid()

            # Disk signature at offset 440
            builder.write_disk_signature()

            builder.fd.save()
        print("  All writes complete.")

    def format_partition1(self):
        """Format partition 1 with the specified filesystem."""
        device = f"{self.disk}s1"
        partition = Disk(device)

        print("\nWaiting for macOS to detect partitions...")
        time.sleep(3)

        partition.unmount()
        time.sleep(1)

        print(f"Formatting {device} as exFAT...")
        partition.format()

    def verify(self):
        """Print final disk layout and verify partition 1 offset."""
        time.sleep(2)
        self.disk.mount()
        time.sleep(1)

        print("\n" + "=" * 50)
        print("Disk layout:")
        print("=" * 50)
        print(self.disk.current_layout)

        partition = Disk(f"{self.disk.device}s1")
        if partition.verify():
            print("  -> Correct! Partition 1 starts at sector 2048 (1MB)")
        else:
            print("  -> WARNING: Partition 1 does not start at sector 2048!")

    def success(self, app):
        """Print success message."""
        print(f"\n{'=' * 50}")
        print(f"Ventoy {app.version} installed successfully!")
        print(f"{'=' * 50}")
        print("\nYou can now copy ISO/WIM/IMG/VHD files to the 'Ventoy' partition.")
        print("Boot from the USB drive and Ventoy will list all bootable images.")

    def run(self):
        """Run the CLI."""
        self.parse_args()
        app = self.app = App(self.args)
        self.disk = app.disk

        self.show_disk_info()

        print(f"\nWorking directory: {app.workdir}")

        print(f"Ventoy version: {app.version}")

        # Download and extract
        app.get_ventoy()

        print("\nBoot images ready:")
        print(f"  boot.img:         {os.path.getsize(app.boot_img)} bytes")
        print(f"  core.img:         {os.path.getsize(app.core_img)} bytes")
        print(f"  ventoy.disk.img:  {os.path.getsize(app.disk_img)} bytes")

        # Build GPT
        print("\nBuilding GPT partition table...")
        app.build_gpt()

        # Final confirmation
        self.confirm("Ready to write. This is your last chance to abort. Proceed?")

        # Write everything
        self.write_to_disk()

        # Format partition 1
        self.format_partition1()

        # Verify
        self.verify()

        # Print success message
        self.success()
