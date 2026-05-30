"""Tests for the basic IO functions (like abort.print(), .err(), .abort()."""

import pytest
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from tests import Stub
from ventoy_macos.logger import Logger
from ventoy_macos.rule import Rule
from ventoy_macos.ux import UX

bp = breakpoint


@pytest.fixture
def ux() -> UX:
    """Return a UX object."""
    return UX()


def test_ux():
    assert UX()


def test_ux_err(ux, capsys):
    ux.err("Goodbye")
    output = capsys.readouterr().err

    assert "Goodbye" in output


@pytest.mark.parametrize(["reply", "expected"], [
    ("y", True),
    ("Y", True),
    ("yes", True),
    ("yes ", True),
    ("yes please", False),
    ("n", False),
    ("q", False),
])
def test_ux_confirm(ux, monkeypatch, reply, expected):
    with monkeypatch.context() as m:
        m.setattr('builtins.input', lambda *_: reply)

        result = ux.confirm("Continue?")

        assert result is expected


def test_ux_console(ux):
    assert isinstance(ux.console, Console)


def test_ux_log(ux):
    assert isinstance(ux.log, Logger)


@pytest.mark.enable_logging
def test_ux_log_start(ux, tmp_path):
    ux.log._path = tmp_path / "log"
    ux.app = Stub(
        args=Stub(
            _get_kwargs=lambda: [("ventoy_version", "1.1.14")]
        )
    )

    ux.log_start()
    log = ux.log.path.read_text()

    assert "Starting." in log
    assert "Option: ventoy_version=1.1.14" in log


@pytest.mark.enable_logging
def test_ux_log_end(ux, tmp_path):
    ux.log._path = tmp_path / "log"

    ux.log_end()
    log = ux.log.path.read_text()

    assert "Done. (ec=None)" in log


@pytest.mark.parametrize(["args", "kwargs", "lines"], [
    (["abc"], {}, "abc"),
    (["abc"], dict(before=5), "\n" * 5),
    (["abc"], dict(after=5), "\n" * 5),
    (["abc"], dict(padding=(0, 10, 0, 10)), "          abc          \n"),
    (["abc"], dict(width=10), "  abc     \n"),
    (["abc", "def"], {}, ["  abc", "  def"]),
])
def test_ux_print(capsys, args, kwargs, lines):
    ux = UX()
    ux.print(*args, **kwargs)

    output = capsys.readouterr().out

    for line in lines:
        assert line in output


@pytest.mark.skip
def test_ux_pause():
    ...


@pytest.mark.skip
def test_ux_confirm():
    ...


@pytest.mark.skip
def test_ux_status():
    ...


@pytest.mark.parametrize(["args", "kwargs", "expected"], [
    ([], {}, "─" * 50,),
    (["hello"], {}, ((line := "─" * 22) + " hello " + line[:-1])),
    (["hello"], {"width": 23}, ((line := "─" * 9) + " hello " + line[:-2])),
])
def test_ux_rule(args, kwargs, expected):
    ux = UX()
    ux.console.width = 50
    hr = ux.rule(*args, **kwargs)
    text = str(next(hr.__rich_console__(ux.console)))

    assert isinstance(hr, Rule)
    assert text == expected


def test_ux_header():
    expected = (line := "─" * 8) + " hello " + line[:-2]
    ux = UX()
    ux.console.width = 21
    hr = ux.rule("hello")
    text = str(next(hr.__rich_console__(ux.console)))

    assert isinstance(hr, Rule)
    assert text == expected


def test_ux_table(capsys):
    ux = UX()
    table = ux.table(
        [("a", "b")],
        headers=["A", "B"],
    )

    ux.print(table)
    output = capsys.readouterr().out
    lines = output.splitlines()

    assert isinstance(table, Table)
    assert "┃ A ┃ B ┃" in lines[1]
    assert "│ a │ b │" in lines[3]


def test_ux_grid(capsys):
    ux = UX()

    grid = ux.grid(
        [("Things:", "1")]
    )
    ux.print(grid)
    output = capsys.readouterr().out

    assert isinstance(grid, Table)
    assert "Things: 1" in output


def test_ux_info_grid(capsys):
    ux = UX()

    grid = ux.info_grid(
        [("Things:", "1")]
    )
    ux.print(grid)
    output = capsys.readouterr().out

    assert isinstance(grid, Table)
    assert "Things: 1" in output


def test_ux_panel(capsys):
    ux = UX()

    panel = ux.panel(
        "Things",
        "things",
    )
    ux.print(panel)
    output = capsys.readouterr().out

    assert isinstance(panel, Panel)
    assert "╭─ Things ──" in output
    assert "│ things" in output


#  @pytest.mark.skip
#  def test_ux_():
#      ...
