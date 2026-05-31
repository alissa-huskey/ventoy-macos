"""Custom rich Prompt."""

from sys import exit

from attr import attr, hasattrs
from rich.console import Console
from rich.prompt import Prompt as RichPrompt

from ventoy_macos import Abort
from ventoy_macos.object import Object

bp = breakpoint


@hasattrs
class Prompt(Object):
    """Ask the user for input."""

    MAX_RETRIES = 10
    RETRIES_NOISY_LIMIT = 3

    ATTRS = {
        "question": None,
        "show_choices": None,
        "choices": [],
        "pre_prompt": None,
        "retries": 0,
        "preface": None,
        "choices_map": {},
    }

    INVALID_PROMPT = (
        "[prompt.invalid]"
        "Try again"
        "[/prompt.invalid]"
    )

    PREFIX = "[prompt.prefix]>[/prompt.prefix]"

    EXCLUDE = [
        "choices",
        "choices_map",
        "hidden",
        "pre_prompt",
        "preface",
        "retries",
        "show_choices",
    ]
    """Keyword arguments to exlude from rich Prompt() construction."""

    QUIT_OPTS = ("q", "quit", "\x03")
    YES_OPTS = ("y", "yes")

    def __init__(self, question: str = None, **kwargs):
        """Initialize.

        Arguments:
            question (str): The question to prompt the user with
            choices (list, optional): A list of choices that the answers should
                be restricted to
            hidden (list, optional): Additional valid answers that will not be
                shown in the prompt if `.show_choices` is `True`
            show_choices (bool, str, default=False):
                when True, add the list of choices to the prompt
                when str, print that text
            pre_prompt (callable, optional): a function to call before each
                time the user is prompted.
            preface (str, optional): A string used by the `.menu()` method,
                printed before the list of choices
        """
        self.question = question
        super().__init__(**kwargs)

        kwargs = {k: v for k, v in kwargs.items() if k not in self.EXCLUDE}

        self.kwargs = kwargs

    @classmethod
    def select(
        cls,
        choices: list,
        preface: str = None,
        hidden: list = [],
        **kwargs,
    ) -> "Prompt":
        """Return a prompt to select from a numbered list of options.

        When .ask() is called, a numbered list of choices will be printed for
        the user to select from. Valid choices include the choices themselves
        as well as the numbers listed beside them. If the user selects a
        number, the returned answer will be the cooresponding choice.

        To allow an empty response, pass hidden=[""].

        Arguments:
            choices (list): The list of options
            preface (str, optional): Text to print before the options
            kwargs: keyword arguments to send to Prompt.select()
        """
        biggest = len(choices)
        numbers = list(map(str, range(1, (biggest + 1))))
        choices_map = dict(zip(numbers, choices))

        prompt = Prompt(
            f"Enter #1-{biggest}",
            choices=choices,
            hidden=((hidden or []) + numbers),
            choices_map=choices_map,
            preface=preface,
            **kwargs,
        )

        def print_menu():
            prompt.console.print(prompt.menu(), highlight=False)

        prompt.pre_prompt = print_menu
        return prompt

    def ask(self) -> str:
        """Repeatedly ask for input until response is valid then return it.

        The prompt text is `.question` the first time, then changed to `Try
        again` when repeated.

        If the `.choices_map` dict is present, the key cooresponding to the
        lower-cased answer will be returned instead of the answer itself.

        Answers will be checked by `.answer_ok()`, and the question will be
        repeated if it fails. Upon repeated invalid responses, the list of
        valid choices will be printed, and eventually the program will abort.

        Answers in `QUIT_OPTS` will cause the program to exit.
        """
        while True:
            # clear out the prompt object on the first retry
            # so that the question will be replaced with INVALID_PROMPT
            if self.retries == 1:
                self._prompt = None

            if self.retries > self.RETRIES_NOISY_LIMIT:
                choices = ", ".join([repr(c) for c in self.choices])
                self.console.print(f"Please enter one of: {choices}")

            answer = self.prompt()

            if self.is_quit(answer):
                exit()

            if self.answer_ok(answer):
                if self.choices_map:
                    answer = self.choices_map.get(answer.lower(), answer)
                return answer

            self.retries += 1

            # abort if there have been too many retries
            if self.retries > self.MAX_RETRIES:
                raise Abort("Giving up.")

    def is_quit(self, answer):
        """Return True if the answer is considered a quit response."""
        return answer.lower() in self.QUIT_OPTS

    def confirm(self) -> bool:
        """Ask a question and return True if the reply is a yes answer."""
        answer = self.prompt()

        if self.is_quit(answer):
            exit()

        return answer.lower() in self.YES_OPTS

    def answer_ok(self, value) -> bool:
        """Return True if the answer is valid."""
        if not self.choices:
            return True
        return value.lower() in self.valid_choices

    @attr
    def message(self):
        """Construct the prompt message.

        Add the prefix and choices text to the question. Change the question to
        "Try again" if `.retries` is not zero.
        """
        question = self.question
        if self.retries:
            question = self.INVALID_PROMPT

        text = (self.PREFIX, question, self.choices_text)
        return " ".join(filter(None, text))

    @attr(method="setter")
    def choices_map(self, value):
        """Set the choices map.

        Ensure all keys are stripped and lowercase.
        """
        if not value:
            return {}
        self._choices_map = {str(k).strip().lower(): v for k, v in value.items()}

    @attr
    def choices_text(self):
        """Return the list of choices to display in the prompt."""
        if not self._choices_text and self.show_choices:
            text = None
            if isinstance(self.show_choices, str):
                text = self.show_choices
            elif self.choices:
                text = "/".join(self.choices)
            if text:
                self._choices_text = rf"[prompt.choices]\[{text}][/prompt.choices]"
        return self._choices_text

    def menu(self) -> str:
        """Return an enumerated list of options for display."""
        lines = []

        if self.preface:
            lines += [self.preface, ""]

        lines += [
            (
                f"  [prompt.number]{i})[/prompt.number] "
                f"[prompt.option]{opt}[/prompt.option]"
            )
            for i, opt in enumerate(self.choices, 1)
        ]

        return "\n".join(lines) + "\n"

    @attr(method="setter")
    def choices(self, value) -> list:
        """Set the list of choices."""
        if not value:
            return []
        self._choices = list(map(str, value))

    @attr(method="setter")
    def hidden(self, value) -> list:
        """Set the list of hidden."""
        if not value:
            return []
        self._hidden = list(map(str, value))

    @property
    def valid_choices(self) -> list:
        """Return a list of normalized choices.

        Includes both choices and hidden choices, stripped and lower case.
        """
        choices = (self.choices or []) + (self.hidden or [])
        return [str(c).strip().lower() for c in (choices)]

    @attr
    def prompt(self) -> RichPrompt:
        """Return the rich prompt object."""
        if not self._prompt:
            self._prompt = RichPrompt(self.message, **self.kwargs)
            if self.pre_prompt:
                self._prompt.pre_prompt = self.pre_prompt
        return self._prompt

    @attr
    def console(self) -> Console:
        """Return a Console object."""
        if not self._console:
            self._console = Console()
        return self._console
