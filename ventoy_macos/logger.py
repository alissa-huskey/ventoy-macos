"""Logger."""

import tempfile
from functools import cached_property, partialmethod
from pathlib import Path

from attr import attr, hasattrs
from loguru import logger
from loguru._logger import Logger as LoguruLogger
from rich.pretty import pretty_repr

from ventoy_macos import VentoyMacosError
from ventoy_macos.object import Object

bp = breakpoint


@hasattrs
class Logger(Object):
    """Rich logger."""

    LINE_CHR = "─"

    @attr
    def path(self) -> Path:
        """Return the path to the log."""
        if not self._path:
            _, file = tempfile.mkstemp()
            print(f"\033[3mTemp log file created at: {file}\033[0m")
            self._path = Path(file)
        return self._path

    @cached_property
    def _logger(self) -> LoguruLogger:
        """Return a python Logger instance."""
        if self.path.is_dir():
            raise VentoyMacosError("Cannot log to dir: {self.path}")

        try:
            logger.remove()
        except ValueError:
            ...

        logger.add(self.path, level="INFO", colorize=True)

        return logger

    def _prepare(self, *args, **kwargs) -> str:
        """Turn args and kwargs into a string for loguru.

        Join args into a space separated string. (Like print()).

        Join kwargs into a series of "; " separated "k=v" strings.

        Combine into one string.
        """
        # an array of for all message strings
        messages = []

        # if args are present, join and add to messages list
        if (args):
            message = " ".join([str(arg) for arg in args])
            messages.append(message)

        # if kwargs are present, join into a series of "k=v" strings,
        # and surround message (if present) in brackets
        # athen add to messages list
        if kwargs:
            if messages:
                messages[0] = f"[{message}]"

            extra = "; ".join([f"{k}={pretty_repr(v)}" for k, v in kwargs.items()])

            messages.append(extra)

        # join all messages into one string
        text = " ".join(messages)

        return text

    def log(self, message: str = None, level: str = None, *args, **kwargs):
        """Write a log message."""
        if message:
            args = (message,) + args

        text = self._prepare(*args, **kwargs)
        self._logger.log(level.upper(), text)

    debug = partialmethod(log, level="DEBUG")
    info = partialmethod(log, level="INFO")
    warn = partialmethod(log, level="WARNING")
    error = partialmethod(log, level="ERROR")
    critical = partialmethod(log, level="CRITICAL")
    success = partialmethod(log, level="SUCCESS")

    @property
    def raw(self):
        """Log a raw message."""
        return self._logger.opt(raw=True)

    def div(self):
        """Log a divider line in the log."""
        self.raw.info(self.LINE_CHR * 100 + "\n")

    def exception(self, ex: BaseException):
        """Log an exception."""
        self._logger.exception(ex)


log_catch = logger.catch
