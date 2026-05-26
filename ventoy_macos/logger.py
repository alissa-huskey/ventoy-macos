"""Logger."""

import tempfile
from functools import cached_property, partialmethod
from pathlib import Path

from attr import attr, hasattrs
from loguru import logger
from loguru._logger import Logger as LoguruLogger

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
            print("\033[3mTemp log file created at: {file}\033[0m")
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

    def log(self, message, level, *args, **kwargs):
        """Write a log message."""
        self._logger.log(level.upper(), message, *args, **kwargs)

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
