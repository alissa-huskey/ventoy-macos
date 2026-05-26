import pytest
from loguru._logger import Logger as LoguruLogger

from ventoy_macos.logger import Logger

bp = breakpoint


@pytest.fixture
def logger(tmp_path):
    """Return a Logger instance."""
    return Logger(path=tmp_path / "test.log")


def test_logger():
    assert Logger()


def test_logger__logger(logger):
    assert isinstance(logger._logger, LoguruLogger)


def test_logger_log(logger):
    logger.log("hello", "WARNING")

    assert logger.path.is_file()
    assert "hello" in (contents := logger.path.read_text())
    assert "WARNING" in contents


def test_logger_warn(logger):
    logger.warn("hello")

    assert logger.path.is_file()
    assert "hello" in (contents := logger.path.read_text())
    assert "WARNING" in contents
