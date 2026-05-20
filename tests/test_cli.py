from pathlib import Path

import pytest

from tests import data
from ventoy_macos import gpt as gpt_module
from ventoy_macos.cli import confirm, die, err, write_to_disk

bp = breakpoint


def test_err(capsys):
    err("Goodbye")
    output = capsys.readouterr().err

    assert "Goodbye" in output


def test_die(capsys):
    with pytest.raises(SystemExit):
        die("Goodbye")


def test_confirm_y(monkeypatch):
    with monkeypatch.context() as m:
        m.setattr('builtins.input', lambda _: "y")

        result = confirm("Continue?")

        assert result is True


def test_confirm_n(monkeypatch):
    with monkeypatch.context() as m:
        m.setattr('builtins.input', lambda _: "n")

        with pytest.raises(SystemExit):
            confirm("Continue?")


@pytest.mark.skip("taking forever, probably need to rethink")
def test_write_to_disk(fs, fixtures_path, monkeypatch, sectors_64g, planned_layout):
    device = Path("/dev/disk67")
    raw_device = Path("/dev/rdisk67")
    fake_images = fixtures_path / "fake_images"
    boot_img_path = fake_images / "boot.img"
    core_img_path = fake_images / "core.img"
    disk_img_path = fake_images / "disk.img"

    fs.create_file(device, contents=b"abcde")
    fs.create_file(raw_device, contents=b"abcde")
    fs.add_real_file(boot_img_path)
    fs.add_real_file(core_img_path)
    fs.add_real_file(disk_img_path)

    with monkeypatch.context() as m:
        m.setattr(gpt_module, "run", lambda args, **kw: None)
        write_to_disk(
            str(raw_device),
            str(device),
            sectors_64g,
            planned_layout,
            data.mbr,
            data.primary,
            data.build_entries,
            data.backup,
            boot_img_path,
            core_img_path,
            disk_img_path,
        )
