import pytest
from loguru import logger

from ventoy_macos.cli import CLI

bp = breakpoint


@pytest.fixture(autouse=True)
def disable_logger():
    """Ensure logs don't print to stdout or workdir."""
    CLI.log = logger
    logger.remove()
    yield
    del CLI.log


@pytest.fixture
def cli() -> CLI:
    """Return a CLI object."""
    return CLI()


def test_cli():
    assert CLI()


def test_cli_err(cli, capsys):
    cli.err("Goodbye")
    output = capsys.readouterr().err

    assert "Goodbye" in output


def test_cli_abort(cli, capsys):
    with pytest.raises(SystemExit):
        cli.abort("Goodbye")


@pytest.mark.parametrize(["reply", "expected"], [
    ("y", True),
    ("Y", True),
    ("yes", True),
    ("yes ", True),
    ("yes please", False),
    ("n", False),
    ("q", False),
])
def test_cli_confirm(cli, monkeypatch, reply, expected):
    with monkeypatch.context() as m:
        m.setattr('builtins.input', lambda *_: reply)

        result = cli.confirm("Continue?")

        assert result is expected


def test_cli_has(cli):
    assert cli.has("xxx") is False
    assert cli.has("echo") is True
