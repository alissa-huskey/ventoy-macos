"""Tests for the basic IO functions (like abort.print(), .err(), .abort()."""

import pytest
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from tests import Stub
from ventoy_macos.cli import CLI
from ventoy_macos.logger import Logger
from ventoy_macos.rule import Rule

bp = breakpoint


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


def test_cli_console(cli):
    assert isinstance(cli.console, Console)


def test_cli_log(cli):
    assert isinstance(cli.log, Logger)


@pytest.mark.enable_logging
def test_cli_log_start(cli, tmp_path):
    cli.log._path = tmp_path / "log"
    cli.app = Stub(
        args=Stub(
            _get_kwargs=lambda: [("ventoy_version", "1.1.14")]
        )
    )

    cli.log_start()
    log = cli.log.path.read_text()

    assert "Starting." in log
    assert "Option: ventoy_version=1.1.14" in log


@pytest.mark.enable_logging
def test_cli_log_end(cli, tmp_path):
    cli.log._path = tmp_path / "log"

    cli.log_end()
    log = cli.log.path.read_text()

    assert "Done. (ec=None)" in log


@pytest.mark.parametrize(["args", "kwargs", "lines"], [
    (["abc"], {}, "abc"),
    (["abc"], dict(before=5), "\n" * 5),
    (["abc"], dict(after=5), "\n" * 5),
    (["abc"], dict(padding=(0, 10, 0, 10)), "          abc          \n"),
    (["abc"], dict(width=10), "  abc     \n"),
    (["abc", "def"], {}, ["  abc", "  def"]),
])
def test_cli_print(capsys, args, kwargs, lines):
    cli = CLI()
    cli.print(*args, **kwargs)

    output = capsys.readouterr().out

    for line in lines:
        assert line in output


@pytest.mark.skip
def test_cli_pause():
    ...


@pytest.mark.skip
def test_cli_confirm():
    ...


@pytest.mark.skip
def test_cli_status():
    ...


@pytest.mark.parametrize(["args", "kwargs", "expected"], [
    ([], {}, "─" * 50,),
    (["hello"], {}, ((line := "─" * 22) + " hello " + line[:-1])),
    (["hello"], {"width": 23}, ((line := "─" * 9) + " hello " + line[:-2])),
])
def test_cli_rule(args, kwargs, expected):
    cli = CLI()
    cli.console.width = 50
    hr = cli.rule(*args, **kwargs)
    text = str(next(hr.__rich_console__(cli.console)))

    assert isinstance(hr, Rule)
    assert text == expected


def test_cli_header():
    expected = (line := "─" * 8) + " hello " + line[:-2]
    cli = CLI()
    cli.console.width = 21
    hr = cli.rule("hello")
    text = str(next(hr.__rich_console__(cli.console)))

    assert isinstance(hr, Rule)
    assert text == expected


def test_cli_table(capsys):
    cli = CLI()
    table = cli.table(
        [("a", "b")],
        headers=["A", "B"],
    )

    cli.print(table)
    output = capsys.readouterr().out
    lines = output.splitlines()

    assert isinstance(table, Table)
    assert "┃ A ┃ B ┃" in lines[1]
    assert "│ a │ b │" in lines[3]


def test_cli_grid(capsys):
    cli = CLI()

    grid = cli.grid(
        [("Things:", "1")]
    )
    cli.print(grid)
    output = capsys.readouterr().out

    assert isinstance(grid, Table)
    assert "Things: 1" in output


def test_cli_info_grid(capsys):
    cli = CLI()

    grid = cli.info_grid(
        [("Things:", "1")]
    )
    cli.print(grid)
    output = capsys.readouterr().out

    assert isinstance(grid, Table)
    assert "Things: 1" in output


def test_cli_panel(capsys):
    cli = CLI()

    panel = cli.panel(
        "Things",
        "things",
    )
    cli.print(panel)
    output = capsys.readouterr().out

    assert isinstance(panel, Panel)
    assert "╭─ Things ──" in output
    assert "│ things" in output


#  @pytest.mark.skip
#  def test_cli_():
#      ...
