"""Custom rich Rule."""

from rich.cells import cell_len, set_cell_size
from rich.console import Console, ConsoleOptions, RenderResult
from rich.rule import Rule as RichRule
from rich.text import Text

bp = breakpoint


class Rule(RichRule):
    r"""Customized rich hoizontal rule.

    Arguments:
        title (Union[str, Text], optional): Text to render in the rule. Defaults to "".
        characters (str, optional): Character(s) used to draw the line. Defaults to "─".
        style (StyleType, optional): Style of Rule. Defaults to "rule.line".
        end (str, optional): Character at end of Rule. defaults to "\\n"
        align (str, optional): How to align the title, one of "left", "center",
            or "right". Defaults to "center".
        end_size (int, optional): For left/right aligned titles, the size of
            the line before/after the title.
        width (int, default=None): Width of the total rule text. Defaults to
            max console width.
    """

    def __init__(
        self,
        *args,
        end_size: int = 0,
        width: int = None,
        **kwargs,
    ):
        """Initialize the object."""
        self.width = width
        self.end_size = end_size
        super().__init__(*args, **kwargs)

    def chars(self, options):
        """Return the line characters (corrected for ascii_only mode)."""
        return (
            "-"
            if (getattr(options, "ascii_only", False) and not self.characters.isascii())
            else self.characters
        )

    def title_text(self, console: Console):
        """Return a renderable object for the title text."""
        if isinstance(self.title, Text):
            title_text = self.title
        else:
            title_text = console.render_str(self.title, style="rule.text")

        title_text.plain = title_text.plain.replace("\n", " ")
        title_text.expand_tabs()
        return title_text

    def __rich_console__(
        self, console: Console, options: ConsoleOptions = None
    ) -> RenderResult:
        """Extend the line before/after the title for left/right aligned rules."""
        width = self.width or getattr(options, "max_width", console.width)
        chars = self.chars(options)
        chars_len = cell_len(chars)
        options = None or console.options

        if not self.title:
            yield self._rule_line(chars_len, width)
            return

        title = self.title_text(console)

        # the spaces before and after the title
        # plus at least one line character before and after the title
        required_space = 4 if self.align == "center" else 2
        if self.align in ("left", "right") and self.end_size:
            required_space += 2

        # maximum title width
        available_space = max(0, width - required_space)
        if not available_space:
            yield self._rule_line(chars_len, width)
            return

        # truncate the title if needed
        title.truncate(available_space, overflow="ellipsis")

        # make the little line that goes at the beginning or end
        if self.end_size:
            end_line = self._rule_line(chars_len, self.end_size)

        max_line_len = width - title.cell_len

        if self.align == "center":
            left = self._rule_line(chars_len, ((max_line_len // 2) // chars_len))
            right = self._rule_line(chars_len, max_line_len - left.cell_len)
            parts = (left, " ", title, " ", right)

        elif self.align == "left":
            line_width = (max_line_len - self.end_size - 1)
            parts = [title, " ", self._rule_line(chars_len, line_width)]

            if self.end_size:
                parts.insert(0, end_line)
                parts.insert(1, " ")

        elif self.align == "right":
            line_width = max_line_len - (self.end_size and self.end_size + 1) - 1
            parts = [self._rule_line(chars_len, line_width), " ", title]

            if self.end_size:
                parts.append(" ")
                parts.append(end_line)

        rule_text = Text.assemble(*parts, end=self.end)
        rule_text.plain = set_cell_size(rule_text.plain, width)

        yield rule_text
