"""Core UX."""

from contextlib import contextmanager
from time import sleep

from attr import attr, hasattrs
from rich.align import Align
from rich.console import Console, Group
from rich.control import Control
from rich.padding import Padding
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.theme import Theme
from rich.traceback import install as rich_tracebacks

from ventoy_macos._exclude import EXCLUDE
from ventoy_macos.logger import Logger
from ventoy_macos.object import Object
from ventoy_macos.prompt import Prompt
from ventoy_macos.rule import Rule

rich_tracebacks(show_locals=True, suppress=EXCLUDE)

bp = breakpoint


@hasattrs
class UX(Object):
    """Contains the core functionality for interacting with the user.

    Printing, reading stdin, formatting data. Does not include application
    logic.
    """

    custom_theme = Theme({
        "checkmark": "green",
        "error": "#af0000",
        "error.epilog": "dim",
        "prompt.choices": "dark_magenta",
        "prompt.invalid": "bright_red",
        "prompt.prefix": "dark_cyan",
        "prompt.option": "none",
        "prompt.number": "bright_blue",
        "rule.line": "purple4",
        "table.border": "dark_cyan",
        "table.header": "bold",
        "warn": "#af0000 bold",
    })

    screen = Control()

    stderr = Console(stderr=True, theme=custom_theme)

    enable_interactive = None

    app = None

    ec = None

    @attr
    def console(self) -> Console:
        """Return a console instance.

        Stored here so that I can disable interactive mode based on --debug
        flag (after object is already initialized) by nulling out ._console and
        setting .enable_interactive to False.
        """
        if not self._console:
            self._console = Console(
                emoji=True,
                width=int(Console().width * 0.9),
                force_interactive=self.enable_interactive,
                theme=self.custom_theme,
            )
        return self._console

    @attr
    def log(self) -> Logger:
        """Return a Logger instance.

        This will be set in run(), but setting it here in case it is needed
        sooner or if that fails.
        """
        if not self._log:
            self._log = Logger()
        return self._log

    def log_start(self):
        """Log the start or end of the program."""
        self.log.div()
        self.log.info("Starting.")
        for name, value in self.app.args._get_kwargs():
            self.log.info(f"Option: {name}={value}")

    def log_end(self):
        """Log the end of the program."""
        self.log.info(f"Done. (ec={self.ec})")
        self.log.div()

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
        icon = "[warn]:warning:[/warn]"
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

        prefix = (prefix or "[error]Error[/error]")

        self.stderr.print(f"{prefix} {message}")

        spaces = Text.from_markup(prefix).cell_len + 1
        for line in lines:
            self.stderr.print(" " * spaces + line, style="error.epilog")

    def done(self, task):
        """Print a task with a checkmark."""
        self.print(f"[checkmark]✔[/checkmark] {task}")

    # ── Interactive ──────────────────────────────────────────────────────

    def pause(self, seconds: int = 1):
        """Pause for `seconds` seconds."""
        sleep(seconds)

    def erase(self, n: int = 1):
        """Remove `n` lines of printed output from the screen.

        Overwrite `n` lines above with spaces then move the cursor up `n`
        lines.
        """
        lines = -(n + 2)

        for i in range(lines, 0):
            print(self.screen.move(0, i))
            print(" " * self.console.width)

        print(self.screen.move(0, lines))

    def ask(self, question: str, persist=True, **kwargs) -> str:
        """Ask a question.

        Arguments:
            question (str): the question
            persist (bool, default=True): if the prompt text should persist in
                stdout. if False, the relevant lines on the screen will be
                cleared and overwritten
            kwargs: keyword arguments to send to Prompt()

        Returns:
            Prompts the user and return the input.
        """
        prompt = Prompt(question, console=self.console, **kwargs)

        if not persist:
            self.erase(prompt.retries + 1)

        answer = prompt.ask()

        # remove the printed prompt output from the screen
        # (go back and clear out the previous lines where the prompt
        # message was printed and leave the cursor there to overwrite)
        #  if not persist:
        #      self.erase()

        return answer

    def confirm(self, question: str, persist=True) -> bool:
        """Ask a yes/no question.

        Arguments:
            question (str): the question
            persist (bool, default=True): if the prompt text should persist in
                stdout. if False, the relevant lines on the screen will be
                cleared and overwritten

        Returns:
            True for a y/Y answer, otherwise False
        """
        prompt = Prompt(
            question,
            console=self.console,
            show_choices="y/N"
        )

        answer = prompt.confirm()

        if not persist:
            self.erase(prompt.retries + 1)

        return answer

    def select(self, choices: list, preface: str = None, **kwargs):
        """Prompt the user to choose from an enumerated list of options.

        Print an numbered list of options and prompt the user to choose one.
        Valid choices include the choices themselves as well as the numbers
        listed beside them.

        Upon receiving invalid options, the question will repeat a number of
        times before finally aborting.

        To allow an empty response, pass hidden=[""].

        Arguments:
            choices (list): The list of options
            preface (str, optional): Text to print before the options
            kwargs: keyword arguments to send to Prompt.select()
        """
        prompt = Prompt.select(
            choices=choices,
            preface=preface,
            console=self.console,
            **kwargs,
        )

        answer = prompt.ask()

        return answer

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
        self.log.info(task)
        if not self.console.is_interactive:
            self.print(f"  {task}...")
            yield

        else:
            with self.console.status(f"{task}..."):
                yield
                if persist:
                    self.done(task)

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
            rows (list[iter]): a list of (name, value) row iterables
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
            columns={0: dict(style="table.header", justify="right")}
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
            border_style="table.border",
            title_align="left",
        )
        options.update(kwargs)

        if title:
            options["title"] = title

        return Panel(
            Group(*data),
            **options,
        )
