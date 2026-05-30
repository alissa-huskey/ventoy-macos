"""CLTableI."""

import sys
from argparse import ArgumentParser, Namespace, RawDescriptionHelpFormatter
from bdb import BdbQuit
from os import geteuid

from rich.panel import Panel

from ventoy_macos import Abort, VentoyMacosWriteError
from ventoy_macos.app import App
from ventoy_macos.common import b2s, run, s2b, size_text
from ventoy_macos.logger import log_catch
from ventoy_macos.ux import UX
from ventoy_macos.workdir import Workdir

bp = breakpoint


class CLI(UX):
    """Everything that prints or receives input from the user."""

    enable_interactive = None

    app = None

    ec = None

    def disk_layout(
        self,
        title: str,
        partitions: list,
        headers: list = [],
        func=None,
        print: bool = False,
    ) -> Panel:
        """Return a panel that contains a disk layout table.

        Arguments:
            title (str): panel title
            partitions (list[Partition]): list of partitions
            header (list[str], optional): additional headers
            func (callable, optional): function to return a list of the
                additional values
            print (bool, default=False): print immediately
        """
        common_headers = ("#", "Name", "Format", "Size")
        table = self.table(
            [
                [
                    str(part.number),
                    part.name,
                    part.fs,
                    size_text(part.sectors),
                    *func(part),
                ]
                for part in partitions
            ],
            headers=([*common_headers, *headers]),
        )
        panel = self.panel(title, table)
        if print:
            self.print(panel)
        return panel

    # ── Validation ───────────────────────────────────────────────────────

    def has(self, cmd: str) -> bool:
        """Return True if command is found on the CLI."""
        result = run(["command", "-v", cmd], check=False)
        return result.returncode == 0

    # ── Command Line Arguments ───────────────────────────────────────────

    def parse_args(self) -> Namespace:
        """Define arguments, parse user input and return results."""
        parser = ArgumentParser(
            description="Install Ventoy on a USB drive from macOS.",
            formatter_class=RawDescriptionHelpFormatter,
            epilog="""
    Examples:
        sudo ventoy-macos /dev/disk4
        sudo ventoy-macos /dev/disk4 --ventoy-version 1.1.10
            """,
        )
        parser.add_argument(
            "disk",
            help="Target disk device (e.g., /dev/disk4)",
        )
        parser.add_argument(
            "-V", "--ventoy-version",
            default=None,
            help="Ventoy version to install (default: latest)",
        )
        parser.add_argument(
            "-d", "--dir",
            default=None,
            help="Working directory for downloads (default: temp directory)",
        )
        parser.add_argument(
            "-D", "--debug",
            default=False,
            action="store_true",
            help="Print tracebacks.",
        )

        self.args = parser.parse_args()

    # ── Program Steps ────────────────────────────────────────────────────

    def validate_sys(self):
        """Check system requirements."""
        if geteuid() != 0:
            raise Abort(
                "This script must be run as root.",
                r"Use: sudo ventoy-macos \[...]",
                prefix=":locked:",
            )

        if sys.platform != "darwin":
            raise Abort("This script is designed for macOS only.")

        if not self.has("xzcat"):
            raise Abort(
                "xz is required but not found.",
                "Install it with: brew install xz"
            )

        if not self.app.workdir.path.is_dir():
            raise Abort(
                f"Invalid working directory: {self.app.workdir}"
            )

        return True

    def validate_disk(self):
        """Check disk requirements."""
        # disk must exist and start with /dev/disk
        if not self.disk.is_disk():
            raise Abort(
                f"Device invalid or not mounted: {self.disk}",
                '(Hint: must start with "/dev/disk".)'
            )

        # must be removable and external
        if not self.disk.is_external():
            raise Abort(
                "Refusing to operate on {self.disk.location}",
                "(It must be removable and external.)",
                prefix=":prohibited:",
            )

        # must not be /dev/disk0 or /dev/disk1
        # (this should be caught by the above,
        # but it can't hurt to double check)
        if self.disk.is_system_disk():
            raise Abort(
                "Refusing to operate on {self.disk.location}",
                "(It is likely a system disk.)",
                prefix=":prohibited:",
            )

        return True

    def get_ventoy(self):
        """Download and extract Ventoy."""
        self.print(self.header("Collecting Ventoy disk images"), before=1, after=1)

        workdir = self.app.workdir

        if not self.app.version:
            if self.confirm("Request latest Ventoy release number?", persist=False):
                with self.status("Fetching version"):
                    self.app.version = Workdir.get_latest()
            else:
                self.print(
                    "Ok. Use the --ventoy-version option next time.",
                    padding=None,
                    before=1,
                )
                exit()

        # skip everything if there are already disk images
        if workdir.has_images():
            self.done(f"Using Ventoy disk images in {workdir.path}")
            workdir.chmod()
            return True

        # if there's already a ventoy dir, skip to decompress
        if workdir.ventoy_dir.is_dir():
            self.done(f"Using Ventoy dir in {workdir.path}")
        else:

            # skip downloading the tarball if it already exists
            if workdir.tarball_path.is_file():
                self.done(f"Using Ventoy tarball in {workdir.path}")
            else:
                if not self.confirm("Download Ventoy?", persist=False):
                    self.print(
                        (
                            "Ok. Next time use --dir to "
                            "point to your local downloads.",
                        ),
                        before=1,
                        padding=None,
                    )
                    exit()

                with self.status(f"Downloading: {workdir.url}"):
                    workdir.download()

            with self.status("Extracting Ventoy package"):
                workdir.extract()

        with self.status("Decompressing disk images"):
            workdir.decompress()

        # give user rw access to all files in workdir
        workdir.chmod()

        return True

    def show_disk_info(self):
        """Print the disk details and layout."""
        panel = self.panel(
            "Target disk",
            self.info_grid([
                ("Name:", self.disk.name or ""),
                ("Partition Scheme:", self.disk.scheme or ""),
                ("Location:", self.disk.location),
                ("Disk size:", f"{self.disk.gb:.1f} GiB ({self.disk.sectors} sectors)")
            ]),
            "\n",
            self.warn("All data on this disk will be destroyed."),
            expand=False,
        )
        self.print(panel)

        if not self.disk.partitions:
            self.print(self.panel(
                "Current Layout",
                "No partitions.",
            ))
        else:
            self.disk_layout(
                "Current Layout",
                self.disk.partitions,
                ["Free", "Identifier"],
                lambda part: [
                    size_text(b2s(part.free)[0]),
                    part.id,
                ],
                print=True,
            )

        self.disk_layout(
            "Planned Layout",
            self.disk.planned_layout,
            ["Sectors"],
            lambda part: [f"[{part.end}-{part.start}]"],
            print=True,
        )

    def write_to_disk(self):
        """Write GPT and Ventoy boot code to the disk."""
        builder = self.app.builder

        with self.status("Unmounting disk"):
            builder.unmount()

        try:
            with builder.fd.open():
                # ── Zero out the partition table headers and PMBR ───────────────────
                # This puts the drive in a known invalid state.

                with self.status("Initializing drive."):
                    builder.init()

                # ── Write disk images ────────────────────────────────────────────────
                # These are the biggest writes and don't mess with the
                # partition table.

                with self.status("Writing core.img"):
                    # sectors 34-2047 (GPT gap area)
                    builder.write_core_img()

                with self.status("Writing ventoy.disk.img to partition 2"):
                    builder.write_disk_img()

                # ── Write most of the partition table ────────────────────────────────

                with self.status("Writing GPT entries"):
                    # sectors 2-33
                    builder.write_entries()

                # offset 92
                with self.status("Writing GPT marker"):
                    builder.write_gpt_marker()

                # offset 17908
                with self.status("Writing second GPT marker"):
                    builder.write_second_gpt_marker()

                # offset 384
                with self.status("Writing disk UUID"):
                    builder.write_disk_uuid()

                # offset 440
                with self.status("Writing disk signature"):
                    builder.write_disk_signature()

                with self.status("Writing protective MBR"):
                    builder.write_mbr()

                with self.status("Writing Ventoy boot.img"):
                    # 446 bytes of BIOS boot code to MBR
                    builder.write_boot_img()

                with self.status("Writing backup GPT"):
                    builder.write_backup()

                # ── Write partition table headers ────────────────────────────────────
                # This puts the drive in a valid state.
                #
                # It is saved for last to reduce the chance of a failure during
                # the write process leaving the drive recognizable as a
                # GPT/Ventoy drive, but broken in an unpredictable way. An
                # known and obvious invalid state is preferable, as it can
                # dependably be recovered by erasing/formatting.

                # sector 1
                with self.status("Writing primary GPT header"):
                    builder.write_primary_header()

                with self.status("Finalizing all writes"):
                    self.log.info("Saving to disk.")
                    builder.fd.save()

        except BaseException as e:
            raise VentoyMacosWriteError("Install failed.", ex=e)

    def format(self):
        """Format partition 1.

        NOTE: I believe this has to be done in a different function than
        write_to_disk(). When I had it in the same function, it seemed that
        macOS didn't finalize the writes untl the function completed, which
        meant that the new partition scheme was not picked up.
        """
        try:
            part = self.disk.partitions[0]
        except IndexError:
            self.line()
            raise Abort(
                "Install failed.",
                f"There are no partitions on disk {self.disk.location}.",
                prefix="  :x:",
            )

        with self.status("Waiting for macOS to detect partitions"):
            self.log.info(f"Unmounting partition 1: {part.location}")
            self.pause(3)
            part.unmount()

        with self.status(f"Formatting {part.location} as exFAT"):
            self.pause()
            part.format()

        return True

    def verify(self):
        """Print final disk layout and verify partition 1 offset."""
        with self.status("Verifying disk"):
            self.pause(2)
            self.log.info(f"Mounting disk: {self.disk.location}")
            self.disk.mount()
            self.pause()

        try:
            partition = self.disk.partitions[0]
        except IndexError:
            self.line()
            raise Abort(
                "Install failed.",
                f"There are no partitions on disk {self.disk.location}.",
                prefix="  :x:",
            )

        if partition.offset != s2b(2048):
            self.line()
            raise Abort(
                "Ventoy disk is corrupted",
                "Partition 1 does not start at sector 2048.",
                prefix="  :x:",
            )
        return True

    def success(self):
        """Print success message."""
        self.ec = 0
        self.log.success(
            f"Ventoy {self.app.version} successfully "
            f"installed on {self.disk.location}"
        )

        self.print(
            f":star: Ventoy {self.app.version} installed successfully! :star:",
            justify="center",
            before=1,
            after=1,
        )

        panel = self.panel(
            "Ventoy Disk",
            self.info_grid([
                ("Name:", self.disk.name or ""),
                ("Partition Scheme:", self.disk.scheme or ""),
                ("Location:", self.disk.location),
                ("Disk size:", f"{self.disk.gb:.1f} GiB ({self.disk.sectors} sectors)"),
            ]),
            expand=False,
        )
        self.print(panel)

        self.disk_layout(
            "Layout",
            self.disk.partitions,
            ["Identifier"],
            lambda part: [part.id],
            print=True,
        )

        self.line(2)

        self.print(
            self.rule(style="dim"),
            "You can now copy ISO/WIM/IMG/VHD files to the 'Ventoy' partition.",
            "Boot from the USB drive and Ventoy will list all bootable images.",
            style="dim",
        )

        return True

    def show_ventoy_info(self):
        """Print ventoy info panel."""
        panel = self.panel(
            None,
            self.info_grid([
                ("Ventoy Version:", self.app.version),
                ("Working Directory:", str(self.app.workdir)),
                ("Log file:", str(self.log.path)),
                ("", ""),
                ("Boot Images", ""),
                *[
                    (img.dest.path.name, f"{img.size} bytes")
                    for img in self.app.workdir.images.values()
                ],
            ]),
            expand=False,
        )
        self.print(panel)
        return True

    @log_catch(reraise=True)
    def run(self):
        """Run the CLI."""
        self.parse_args()

        self.app = App(self.args)
        self.app.workdir.mkdirs()
        self.disk = self.app.disk
        self.log = self.app.log
        self.log_start()

        # disable interactive mode while in debug mode
        # otherwise breakpionts cause problems
        if self.app.args.debug:
            self.enable_interactive = False
            self.console = None

        if self.app.args.debug:
            self.console.force_interactive = False

        self.validate_sys()

        self.get_ventoy()

        self.print(self.header("Summary"), before=1)

        self.show_ventoy_info()

        self.validate_disk()
        self.show_disk_info()

        self.print(
            self.warn("This is your last chance to abort."),
            before=1,
            after=1,
        )

        if not self.confirm(f"Proceed with device: [b]{self.disk.location}[/b]?"):
            return

        self.print(self.header("Building Ventoy disk"), before=1, after=1)

        parts = [
            {"id": p.id, "fs": p.fs, "offset": p.offset, "size": size_text(p.gb)}
            for p in self.disk.partitions
        ]
        self.log.info("before", info=self.disk.info, partitions=parts)

        # Write everything
        self.write_to_disk()

        self.format()

        self.log.info("after", info=self.disk.info, partitions=parts)

        # Verify
        if self.verify():
            self.success()


@log_catch(reraise=True)
def main():
    """Run the program."""
    try:
        cli = CLI()
        cli.run()

    # clean exits
    except (BdbQuit, KeyboardInterrupt, SystemExit):
        cli.ec = 0
        print()

    # user errors
    except Abort as e:
        cli.ec = 1
        cli.log.error("\n".join(e.args))
        cli.err(*e.args, **e.kwargs)
        exit(2)

    except VentoyMacosWriteError as e:
        cli.ec = 1
        cli.line(2)
        cli.err("Install failed.", str(e.ex), prefix=":collision:")
        cli.line(1)

        print(
            f"The disk: {cli.disk.location} may not be formatted.",
            "Strongly recommend erasing/formatting before use.",
            sep="\n",
        )

        exit(1)
    except BaseException as e:
        cli.ec = 1
        if cli.app and cli.app.args and cli.app.args.debug:
            # print the traceback if in debug mode
            cli.console.print_exception()
            exit(1)

        else:
            # otherwise print a shorter and prettier error message
            cli.err(
                "Something went wrong unexpectedly.",
                f"{e.__class__.__name__}: {e}",
                "See the log for more details",
                prefix=":collision:",
            )

    finally:
        cli.log_end()
