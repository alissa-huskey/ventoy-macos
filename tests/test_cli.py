import pytest

from ventoy_macos.cli import CLI

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


def test_cli_die(cli, capsys):
    with pytest.raises(SystemExit):
        cli.die("Goodbye")


def test_cli_confirm_y(cli, monkeypatch):
    with monkeypatch.context() as m:
        m.setattr('builtins.input', lambda _: "y")

        result = cli.confirm("Continue?")

        assert result is True


def test_cli_confirm_n(cli, monkeypatch):
    with monkeypatch.context() as m:
        m.setattr('builtins.input', lambda _: "n")

        with pytest.raises(SystemExit):
            cli.confirm("Continue?")


def test_cli_has(cli):
    assert cli.has("xxx") is False
    assert cli.has("echo") is True
