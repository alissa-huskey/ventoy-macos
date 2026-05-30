from contextlib import contextmanager
from pathlib import Path

import pytest

from tests import Stub, noop, noop_context, return_false, return_true
from ventoy_macos import Abort
from ventoy_macos import cli as cli_module
from ventoy_macos import ux as ux_module
from ventoy_macos.cli import CLI
from ventoy_macos.common import g2s
from ventoy_macos.disk import Disk

bp = breakpoint


class BuilderStub(Stub):
    """Builder stub."""

    @property
    def fd(self):
        """Return stub FD object."""
        return Stub(
            open=noop_context,
            save=noop,
        )

    def __getattr__(self, name: str):
        """Return noop callable for missing attributes."""
        return noop


@pytest.fixture
def assert_abort():
    """Assert that the operation calls an Abort exception."""
    @contextmanager
    def wrapper(message: str = None):
        with pytest.raises(Abort) as e:
            yield
        ex = e.value
        if message:
            assert message in str(ex)

    return wrapper


@contextmanager
def mock_status(task):
    """Mock CLI.status()."""
    print("  " + task)
    yield


def mock_confirm(message, **k):
    """Mock CLI.confirm()."""
    print(message, "\n")
    return True


@pytest.fixture
def disk_stub(planned_layout) -> Disk:
    """Return a Disk object."""
    return Disk(
        name="NO NAME",
        scheme="GUID_partition_scheme",
        location="/dev/disk4",
        size=63995012710,
        partitions=[],
        planned_layout=planned_layout,
    )


@pytest.fixture
def app_stub(tmp_path, disk_stub):
    """Return a stub of an App object."""
    return Stub(
        version="1.1.11",
        disk=disk_stub,
        chmod=noop,
        workdir=Stub(
            chmod=noop,
            decompress=noop,
            download=noop,
            extract=noop,
            has_images=return_false,
            path=tmp_path,
            request=lambda *a: Stub(ok=True),
            tarball_path=Stub(is_file=return_true),
            url="https://github.com/...",
            ventoy_dir=Stub(is_dir=return_true),
            version="1.1.11",
            images={
                "boot_img": Stub(
                    dest=Stub(exists=return_true, path=Stub(name="boot.img")),
                    decompress=noop,
                    size=512,
                ),
            },
        ),
    )


@pytest.fixture()
def mock_get_latest(monkeypatch):
    """Mock dir.get_latest()."""
    with monkeypatch.context() as m:
        m.setattr(cli_module.Workdir, "get_latest", noop)
        yield


@pytest.fixture
def cli(app_stub, disk_stub):
    """Return a CLI object with key attrs mocked/stubbed."""
    return CLI(
        app=app_stub,
        confirm=mock_confirm,
        status=mock_status,
        disk=disk_stub,
    )


def test_cli_disk_layout(capsys, planned_layout):
    cli = CLI()

    cli.disk = Disk(
        name="NO NAME",
        scheme="GUID_partition_scheme",
        location="/dev/disk4",
        size=63995012710,
        partitions=[],
        planned_layout=planned_layout,
    )

    cli.show_disk_info()

    output = capsys.readouterr().out

    assert "Name: NO NAME" in output
    assert "Partition Scheme: GUID_partition_scheme" in output
    assert "Location: /dev/disk4" in output
    assert "Disk size: 59.6 GiB (124990259 sectors)" in output

    assert "No partitions." in output

    assert "1 │ Ventoy  │ exFAT  │ 59.6 GiB │ [124934423-2048]" in output
    assert "2 │ VTOYEFI │ FAT16  │ 31 MiB   │ [124999959-124934424]" in output


def test_cli_validate_sys_not_sudo(assert_abort):
    with assert_abort("must be run as root"):
        cli = CLI()
        cli.validate_sys()


def test_cli_validate_sys_not_macos(monkeypatch, assert_abort):
    with monkeypatch.context() as m:
        m.setattr(cli_module, "geteuid", lambda: 0)
        m.setattr("sys.platform", "windows")

        with assert_abort("for macOS only"):
            cli = CLI()
            cli.validate_sys()


def test_cli_validate_sys_no_xzcat(monkeypatch, assert_abort):
    with monkeypatch.context() as m:
        m.setattr(cli_module, "geteuid", lambda: 0)
        m.setattr("sys.platform", "darwin")

        cli = CLI()
        cli.has = lambda self: False

        with assert_abort("xz is required"):
            cli.validate_sys()


def test_cli_validate_sys_invalid_workdir(monkeypatch, assert_abort, cli):
    with monkeypatch.context() as m:
        m.setattr(cli_module, "geteuid", lambda: 0)
        m.setattr("sys.platform", "darwin")
        m.setattr(cli.app.workdir, "path", Path("xxxxxxxxx"))
        m.setattr(cli, "has", return_true)

        with assert_abort("Invalid working directory"):
            cli.validate_sys()


def test_cli_validate_sys(monkeypatch, tmp_path, cli):
    with monkeypatch.context() as m:
        m.setattr(cli_module, "geteuid", lambda: 0)
        m.setattr("sys.platform", "darwin")
        m.setattr(cli, "has", return_true)

        assert cli.validate_sys()


def test_cli_validate_disk_not_disk(assert_abort):
    with assert_abort("Device invalid or not mounted"):
        cli = CLI()
        cli.disk = Stub(is_disk=lambda: False)
        cli.validate_disk()


def test_cli_validate_disk_not_external(assert_abort):
    with assert_abort("must be removable and external"):
        cli = CLI()
        cli.disk = Stub(is_disk=lambda: True, is_external=lambda: False)
        cli.validate_disk()


def test_cli_validate_disk_system_disk(assert_abort):
    with assert_abort("likely a system disk"):
        cli = CLI()
        cli.disk = Stub(
            is_disk=lambda: True,
            is_external=lambda: True,
            is_system_disk=lambda: True,
        )
        cli.validate_disk()


def test_cli_validate_disk():
    cli = CLI()
    cli.disk = Stub(
        is_disk=lambda: True,
        is_external=lambda: True,
        is_system_disk=lambda: False,
    )
    assert cli.validate_disk()


def test_cli_get_ventoy_with_version(mock_get_latest, capsys, cli):
    """
    GIVEN: A workdir that exists
    AND: .app.version is set
    WHEN: .get_ventoy() is called
    THEN: it should not ask if you want to get the latest vetoy version
    AND: it should not try to fetch the latest version
    AND: it should say that it will use the disk images in workdir
    AND: it should return True
    """
    result = cli.get_ventoy()
    output = capsys.readouterr().out

    assert "Request latest Ventoy release number?" not in output
    assert "Fetching version" not in output
    assert result is True


def test_cli_get_ventoy_without_version(mock_get_latest, capsys, cli):
    """
    GIVEN: A workdir that exists
    AND: .app.version is set
    WHEN: .get_ventoy() is called
    THEN: it should not ask if you want to get the latest vetoy version
    AND: it should not try to fetch the latest version
    AND: it should say that it will use the disk images in workdir
    AND: it should return True
    """
    cli.app.version = None
    result = cli.get_ventoy()
    output = capsys.readouterr().out

    assert "Request latest Ventoy release number?" in output
    assert "Fetching version" in output
    assert result is True


def test_cli_get_ventoy_with_disk_images(mock_get_latest, capsys, cli):
    """
    GIVEN: A workdir that exists
    AND: all app.images exist in that dir
    WHEN: .get_ventoy() is called
    THEN: it should say that it's using those disk images
    AND: it should return True
    """
    cli.app.workdir.has_images = return_true
    result = cli.get_ventoy()
    output = capsys.readouterr().out

    assert "Using Ventoy disk images" in output
    assert result is True


def test_cli_get_ventoy_without_disk_images(mock_get_latest, capsys, cli):
    """
    GIVEN: A workdir that exists
    AND: all app.images are not in that dir
    WHEN: .get_ventoy() is called
    THEN: it should not say that it's using those disk images
    AND: it should decompress those images (at some point)
    AND: it should return True
    """
    cli.app.workdir.has_images = return_false
    result = cli.get_ventoy()
    output = capsys.readouterr().out

    assert "Using Ventoy disk images" not in output
    assert "Decompressing disk images" in output
    assert result is True


def test_cli_get_ventoy_with_ventoy_dir(mock_get_latest, capsys, cli):
    """
    GIVEN: A workdir that exists
    AND: all app.images are not in that dir
    AND: ventoy-x-x-xx is in that dir
    WHEN: .get_ventoy() is called
    THEN: it should not say it is using a dir
    AND: it should extract the dir from a tarball (at some point)
    AND: it should decompress the disk images
    AND: it should return True
    """
    cli.app.workdir.has_images = return_false
    result = cli.get_ventoy()
    output = capsys.readouterr().out

    assert "Using Ventoy dir" in output
    assert "Decompressing disk images" in output
    assert result is True


def test_cli_get_ventoy_without_ventoy_dir(mock_get_latest, capsys, cli):
    """
    GIVEN: A workdir that exists
    AND: all app.images are not in that dir
    AND: ventoy-x-x-xx is not in that dir
    WHEN: .get_ventoy() is called
    THEN: it should not say it is using that dir
    AND: it should (eventally) extract the dir from a tarball
    AND: it should decompress the disk images
    AND: it should return True
    """
    cli.app.workdir.has_images = return_false
    cli.app.workdir.ventoy_dir.is_dir = return_false

    result = cli.get_ventoy()
    output = capsys.readouterr().out

    assert "Using Ventoy dir" not in output
    assert "Extracting Ventoy package" in output
    assert "Decompressing disk images" in output
    assert result is True


def test_cli_get_ventoy_without_tarball(mock_get_latest, capsys, cli):
    """
    GIVEN: A workdir that exists
    AND: all app.images are not in that dir
    AND: ventoy-x-x-xx is not in that dir
    AND: a tarball is not in that dir
    WHEN: .get_ventoy() is called
    THEN: it should not say it is using that tarball
    AND: it should ask if you want to download ventoy
    AND: it should say it is downloading that tarball
    AND: it should extract the dir from a tarball
    AND: it should decompress the disk images
    AND: it should return True
    """
    cli.app.workdir.tarball_path.is_file = return_false
    cli.app.workdir.has_images = return_false
    cli.app.workdir.ventoy_dir.is_dir = return_false

    result = cli.get_ventoy()
    output = capsys.readouterr().out

    assert "Using Ventoy tarball" not in output
    assert "Download Ventoy?" in output
    assert "Downloading:" in output
    assert "Extracting Ventoy package" in output
    assert "Decompressing disk images" in output
    assert result is True


def test_cli_get_ventoy_with_tarball(mock_get_latest, capsys, cli):
    """
    GIVEN: A workdir that exists
    AND: all app.images are not in that dir
    AND: ventoy-x-x-xx is not in that dir
    AND: a tarball is in that dir
    WHEN: .get_ventoy() is called
    THEN: it should say it is using that tarball
    AND: it should not ask if you want to download ventoy
    AND: it should not say it is downloading that tarball
    AND: it should extract the dir from a tarball
    AND: it should decompress the disk images
    AND: it should return True
    """
    cli.app.workdir.tarball_path.is_file = return_true
    cli.app.workdir.has_images = return_false
    cli.app.workdir.ventoy_dir.is_dir = return_false

    result = cli.get_ventoy()
    output = capsys.readouterr().out

    assert "Using Ventoy tarball" in output
    assert "Download Ventoy?" not in output
    assert "Downloading:" not in output
    assert "Extracting Ventoy package" in output
    assert "Decompressing disk images" in output
    assert result is True


def test_cli_format(monkeypatch, cli, capsys, planned_layout):
    cli.disk.partitions = planned_layout
    cli.disk.partitions[0].location = "/dev/disk4s1"

    with monkeypatch.context() as m:
        m.setattr(cli.disk.partitions[0], "format", noop)
        m.setattr(cli.disk.partitions[0], "unmount", noop)
        m.setattr(ux_module, "sleep", noop)
        result = cli.format()
        output = capsys.readouterr().out

    assert "Waiting for macOS to detect partitions" in output
    assert "Formatting /dev/disk4s1 as exFAT" in output

    assert result


def test_cli_success(capsys, planned_layout):
    """
    GIVEN: ...
    WHEN: .success() is called
    THEN: it should say it completed successfully
    AND: it should print the drive info
    AND: it should print the partition layout
    AND: it should print a message about usage
    AND: .ec should be 0
    AND: it should return True
    """
    planned_layout[0].id = "/dev/disk4s1"
    planned_layout[1].id = "/dev/disk4s2"

    cli = CLI(
      app=Stub(version="1.1.11"),
      disk=Stub(
        location="/dev/disk4",
        gb=64,
        sectors=g2s(64),
        name="Flash Drive",
        scheme="GUID_partition_scheme",
        partitions=planned_layout,
      ),
    )

    result = cli.success()
    output = capsys.readouterr().out

    assert "Ventoy 1.1.11 installed successfully!" in output
    assert "Name: Flash Drive" in output
    assert "Partition Scheme: GUID_partition_scheme" in output
    assert "Location: /dev/disk4" in output
    assert "Disk size: 64.0 GiB (134217728 sectors)" in output
    assert "Boot from the USB drive" in output
    assert "1 │ Ventoy  │ exFAT  │ 59.6 GiB │ /dev/disk4s1" in output
    assert "2 │ VTOYEFI │ FAT16  │ 31 MiB   │ /dev/disk4s2" in output
    assert cli.ec == 0
    assert result is True


def test_cli_show_ventoy_info(capsys, cli):
    cli.log.path = "/tmp/ventoy-macos.log"
    cli.show_ventoy_info()
    output = capsys.readouterr().out

    assert "Ventoy Version: 1.1.11" in output
    assert "Working Directory:" in output
    assert "Log file: /tmp/ventoy-macos.log" in output
    assert "boot.img 512 bytes" in output


def test_cli_write_to_disk(monkeypatch, capsys, cli):
    with monkeypatch.context() as m:
        m.setattr(ux_module, "sleep", noop)

        cli.app.builder = BuilderStub()

        cli.write_to_disk()

        output = capsys.readouterr().out

        assert "Unmounting disk" in output
        assert "Initializing drive." in output
        assert "Writing core.img" in output
        assert "Writing ventoy.disk.img to partition 2" in output
        assert "Writing GPT entries" in output
        assert "Writing GPT marker" in output
        assert "Writing second GPT marker" in output
        assert "Writing disk UUID" in output
        assert "Writing disk signature" in output
        assert "Writing protective MBR" in output
        assert "Writing Ventoy boot.img" in output
        assert "Writing backup GPT" in output
        assert "Writing primary GPT header" in output
        assert "Finalizing all writes" in output

        assert output


def test_cli_has(cli):
    assert cli.has("xxx") is False
    assert cli.has("echo") is True


@pytest.mark.skip
def test_cli_run():
    """
    GIVEN: ...
    WHEN: ...
    THEN: ...
    """


#  @pytest.mark.skip
#  def test_cli_():
#      """
#      GIVEN: ...
#      WHEN: ...
#      THEN: ...
#      """
