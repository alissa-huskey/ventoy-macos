import pytest

from ventoy_macos.cli import confirm, die, err

bp = breakpoint


def test_err(capsys):
    err("Goodbye")
    output = capsys.readouterr().err

    assert "Goodbye" in output


def test_die(capsys):
    with pytest.raises(SystemExit):
        die("Goodbye")


def test_confirm_y(monkeypatch):
    monkeypatch.setattr('builtins.input', lambda _: "y")

    result = confirm("Continue?")

    assert result is True


def test_confirm_n(monkeypatch):
    monkeypatch.setattr('builtins.input', lambda _: "n")

    with pytest.raises(SystemExit):
        confirm("Continue?")
