"""CLI."""

import sys
from argparse import ArgumentParser, Namespace, RawDescriptionHelpFormatter
from bdb import BdbQuit
from contextlib import contextmanager
from os import geteuid
from os.path import getsize
from time import sleep

from rich.align import Align
from rich.console import Console, Group
from rich.control import Control
from rich.padding import Padding
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text
from rich.traceback import install as rich_tracebacks

from ventoy_macos import VentoyMacosError
from ventoy_macos.app import App
from ventoy_macos.builder import Builder
from ventoy_macos.common import run, size_text
from ventoy_macos.disk import Disk
from ventoy_macos.rule import Rule

rich_tracebacks(show_locals=True)

bp = breakpoint


class CLI():
    """Everything that prints or receives input from the user."""

    console = Console(
        emoji=True,
        width=int(Console().width * 0.9),
    )

    screen = Control()

    stderr = Console(stderr=True)

    SECONDS = 1

    app = None

    # ── Printing ─────────────────────────────────────────────────────────

    def print(
        self,
        *renderables,
        before: int = None,
        after: int = None,
        padding: tuple = (0, 3, 0, 2),
        width=None,
        **kwargs,
    ):
        """Print to stdout.

        Arguments:
            renderables: an iterable of renderables to print
            before (int): number of lines to print before
            after (int): number of lines to print after
            padding (tuple[int]): a tuple of (top, right, bottom, left) padding values
            width (int, float): width; if a float is passed, the percentage of
                console rows is calculated and passed to console.print()
        """
        if before:
            self.console.print("\n" * before)

        for obj in renderables:
            if padding:
                obj = Padding(obj, padding)

            if isinstance(width, float):
                width = int(self.console.width * width)

            self.console.print(obj, width=width, **kwargs)

        if after:
            self.console.print("\n" * after)

    def line(self, lines: int = 1):
        """Print one or more blank lines."""
        self.console.line(lines)

    # ── User messages ────────────────────────────────────────────────────

    def warn(self, message: str, print: bool = False) -> Align:
        """Return and optionally print a warning message.

        Arguments:
            message (str): warning text
            print (bool, default=False): print the warning immediately

        Returns:
            Align renderable (centered)
        """
        icon = "[warning]:warning:[/warning]"
        message = Align(
            f"{icon} Warning: {message} {icon}",
            align="center",
        )
        if print:
            self.print(message)
        return message

    def err(self, *message, prefix=None):
        """Print one or more error message lines to stderr.

        The default error message is prefixed with a red "Error" string. If
        `prefix` is passed, that will be used instead.

        If message is an iterable of multiple lines, only the first line will
        include the prefix. All following lines will be indented to align with
        the first message, and styled gray/dim.

        Arguments:
            message (str, list[str]): messages or list of message lines to
                print to stderr
            prefix (str, optional): alternate error messsage prefix
        """
        if isinstance(message, str):
            lines = []
        else:
            lines = list(message)
            message = lines.pop(0)

        prefix = (prefix or "[#af0000]Error[/#af0000]")

        self.stderr.print(f"{prefix} {message}")

        spaces = Text.from_markup(prefix).cell_len + 1
        for line in lines:
            self.stderr.print(" " * spaces + line, style="dim")

    def abort(self, *message, **kwargs):
        """Print an error message and exit."""
        self.err(*message, **kwargs)
        sys.exit(1)

    # ── Interactive ──────────────────────────────────────────────────────

    def pause(self, seconds: int = 1):
        """Pause for `seconds` seconds."""
        sleep(seconds)

    def confirm(self, prompt: str, persist=True) -> bool:
        """Ask a yes/no question.

        Arguments:
            prompt (str): the question
            persist (bool, default=True): if the prompt text should persist in
                stdout. if False, the relevant lines on the screen will be
                cleared and overwritten

        Returns:
            True for a y/Y answer, otherwise False
        """
        answer = Prompt.ask(
            "  "
            "[green1]>[/green1] "
            fr"{prompt} [dark_magenta]\[y/n]"
        )

        # remove the printed prompt output from the screen
        # (go back and clear out the previous lines where the prompt
        # message was printed and leave the cursor there to overwrite)
        if not persist:
            print(self.screen.move(0, -2))
            print(" " * self.console.width)
            print(self.screen.move(0, -2))

        return answer.lower() == "y"

    @contextmanager
    def status(self, task: str, persist: bool = True):
        """Status spinner.

        Context manager to display an animated status spinner while the task is
        running. If `persist` is True, also print checkmark and task name to
        stdout.

        Arguments:
            task (str): task description
            persist (bool, default=True): if the message should persist (by
                printing a checkmark line to stdout after the task has completed)
        """
        with self.console.status(f"{task}..."):
            yield
            if persist:
                self.print(f"[green]✔[/green] {task}")

    # ── Layout and Formattng ─────────────────────────────────────────────

    def rule(self, *args, print: bool = False, **kwargs) -> Rule:
        """Return and optionally print a horizontal rule.

        Arguments:
            title (str): the rule title
            print (bool, default=False): if True, print immediately
            kwargs: Rule() options

        """
        rule = Rule(*args, **kwargs)
        if print:
            self.print(rule)
        return rule

    def header(self, title: str, print: bool = False) -> Rule:
        """Return and optionally print a section header.

        Arguments:
            title (str): section header text
            print (bool, default=False): if True, print immediately
        """
        rule = self.rule(
            title,
            align="left",
            end_size=2,
            style="green",
        )

        if print:
            self.print(rule)

        return rule

    def table(self, rows: list, headers: list = [], options: dict = {}) -> Table:
        """Return a rich Table.

        Arguments:
            rows (iter): a list of iterable rows
            headers (iter, optional): an interable of header strings
            options (dict): Table() options
        """
        table = Table(*headers, **options)
        for row in rows:
            table.add_row(*row)
        return table

    def grid(self, rows: list, columns={}) -> Table:
        """Return a rich table object with no lines, headers or footers.

        Arguments:
            rows (list[iter]): a row of (name, value) iterables
            columns (dict, optional): a dictionary of (column_number ->
                options) to pass to `.add_column()`.
        """
        if not len(rows):
            return ""

        grid = Table.grid(padding=(0, 1, 0, 1))

        for i in range(len(rows[0])):
            options = columns.get(i, {})
            grid.add_column(**options)

        for row in rows:
            grid.add_row(*row)

        return grid

    def info_grid(self, rows: list) -> Table:
        """Return a table for displaying field list data.

        Arguments:
            rows (list[iter]): a row of (name, value) iterables

        Example:
            >>> table = self.info_grid([
            ...    ("Location:", "/dev/disk4"),
            ...    ("Disk size:", "5.0 GiB (10485672 sectors)"),
            ... ])
            >>> self.print(table)
             Location: /dev/disk4
            Disk size: 5.0 GiB (10485672 sectors)
        """
        return self.grid(
            rows=rows,
            columns={0: dict(style="bold", justify="right")}
        )

    def panel(self, title: str, *data, **kwargs) -> Panel:
        """Return a stylized rich Panel.

        Arguments:
            title (str): panel title
            data (renderable, list[renderable]): an object renderable by rich
                or an iterable of the same to display in this panel
            kwargs: Panel() options
        """
        options = dict(
            border_style="dark_cyan",
            title_align="left",
        )
        options.update(kwargs)

        return Panel(
            Group(*data),
            title=title,
            **options,
        )

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
                    part.format,
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
        parser.add_argument(
            "--debug",
            default=False,
            action="store_true",
            help="Print tracebacks.",
        )

        self.args = parser.parse_args()

    # ── Program Steps ────────────────────────────────────────────────────

    def validate(self):
        """Check system and disk requirements."""
        if geteuid() != 0:
            self.abort(
                "This script must be run as root.",
                r"Use: sudo ventoy-macos \[...]",
                prefix=":locked:",
            )

        if sys.platform != "darwin":
            self.abort("This script is designed for macOS only.")

        if not self.has("xzcat"):
            self.abort(
                "xz is required but not found.",
                "Install it with: brew install xz"
            )

        # disk must exist and start with /dev/disk
        if not self.disk.is_disk():
            self.abort(
                f"Device not found or invalid: {self.disk}",
                '(Hint: must start with "/dev/disk".)'
            )

        # must be removable and external
        if not self.disk.is_external():
            self.abort(
                "Refusing to operate on {self.disk.device}",
                "(It must be removable and external.)",
                prefix=":prohibited:",
            )

        # must not be /dev/disk0 or /dev/disk1
        # (this should be caught by the above,
        # but it can't hurt to double check)
        if self.disk.is_system_disk():
            self.abort(
                "Refusing to operate on {self.disk.device}",
                "(It is likely a system disk.)",
                prefix=":prohibited:",
            )

    def show_disk_info(self):
        """Print the disk details and layout."""
        panel = self.panel(
            "Target disk",
            self.info_grid([
                ("Location:", self.disk.device),
                ("Disk size:", f"{self.disk.gb:.1f} GiB ({self.disk.sectors} sectors)")
            ]),
            "\n",
            self.warn("All data on this disk will be destroyed."),
            expand=False,
        )
        self.print(panel, before=1)

        self.disk_layout(
            "Current Layout",
            self.disk.current_layout,
            ["Identifier"],
            lambda part: [part.identifier],
            print=True,
        )

        self.disk_layout(
            "Planned Layout",
            self.disk.planned_layout,
            ["Sectors"],
            lambda part: [f"[{part.start}-{part.start}]"],
            print=True
        )

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

        with self.status("Unmounting disk"):
            builder.unmount()

        with builder.fd.open():
            # (protective MBR + GPT header + entries area)
            with self.status("Zeroing first 1MB"):
                builder.write_init_header()

            with self.status("Zeroing backup GPT area"):
                builder.write_init_backup()

            with self.status("Writing protective MBR"):
                builder.write_mbr()

            # sector 1
            with self.status("Writing primary GPT header"):
                builder.write_primary_header()

            # sectors 2-33
            with self.status("Writing GPT entries"):
                builder.write_entries()

            # (+ header)
            with self.status("Writing backup GPT"):
                builder.write_backup()

            with self.status("Writing Ventoy boot.img"):
                # 446 bytes of BIOS boot code to MBR
                builder.write_boot_img()

                # GPT marker at offset 92
                builder.write_gpt_marker(92, b"\x22")

            with self.status("Writing core.img"):
                # sectors 34-2047 (GPT gap area)
                builder.write_core_img()

                # Second GPT marker at offset 17908
                builder.write_second_gpt_marker()

            with self.status("Writing ventoy.disk.img to partition 2"):
                builder.write_disk_img()

                # Disk UUID at offset 384
                builder.write_disk_uuid()

                # Disk signature at offset 440
                builder.write_disk_signature()

            with self.status("Finalizing all writes"):
                builder.fd.save()

    def verify(self):
        """Print final disk layout and verify partition 1 offset."""
        with self.status("Verifying disk", persist=False):
            self.pause(2)
            self.disk.mount()
            self.pause()

        partition = Disk(f"{self.disk.device}s1")
        if not partition.verify():
            self.line()
            self.abort(
                "Ventoy disk is corrupted",
                "Partition 1 does not start at sector 2048.",
                prefix="  :x:",
            )

        self.print(
            ":star: Ventoy {self.app.version} installed successfully! :star:",
            justify="center",
            before=1,
            after=1,
        )

        self.disk_layout(
            "New Disk Layout",
            self.disk.current_layout,
            ["Identifier"],
            lambda part: [part.identifier],
            print=True,
        )

        self.line(2)

        self.print(
            self.rule(style="dim"),
            "You can now copy ISO/WIM/IMG/VHD files to the 'Ventoy' partition.",
            "Boot from the USB drive and Ventoy will list all bootable images.",
            style="dim",
        )

    def run(self):
        """Run the CLI."""
        self.parse_args()

        app = self.app = App(self.args)
        self.disk = app.disk

        self.validate()
        self.show_disk_info()

        if not self.confirm("Download ventoy?", persist=False):
            return

        # Download and extract
        with self.status("Downloading Ventoy", persist=False):
            app.get_ventoy()

        panel = self.panel(
            "Build",
            self.info_grid([
                ("Ventoy version:", "1.1.12"),
                ("Working directory:", "/tmp"),
                *[
                    (name, (getsize(getattr(self.app, name)) + " bytes"))
                    for name, size in ["boot.img", "core.img", "ventoy.disk.img"]
                ],
            ]),
        )
        self.print(panel)

        self.print(
            self.warn("This is your last chance to abort."),
            before=1,
            after=1,
        )

        if not self.confirm(f"Proceed with device: [b]{self.disk.device}[/b]?"):
            return

        self.print(self.header("Building Ventoy disk"), before=1, after=1)

        # Build GPT
        with self.status("Building GPT partition table"):
            app.build_gpt()

        # Write everything
        self.write_to_disk()

        # Format partition 1
        self.format_partition1()

        # Verify
        self.verify()


def main():
    """Run the program."""
    try:
        cli = CLI()
        cli.run()

    except VentoyMacosError as e:
        if cli.app and cli.app.args and cli.app.args.debug:
            # print the traceback if in debug mode
            cli.console.print_exception()
            exit(1)

        else:
            # otherwise print a shorter and prettier error message
            cli.abort(
                "Something went wrong unexpectedly.",
                str(e),
                prefix=":collision:",
            )

    # quit the debugger cleanly
    except BdbQuit:
        ...
