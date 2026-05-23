"""Bootable USB Builder."""

from os import urandom
from time import sleep
from uuid import uuid4

from ventoy_macos import SECTOR_SIZE, VentoyMacosError
from ventoy_macos.common import b2s, s2b
from ventoy_macos.disk import Disk
from ventoy_macos.fd import FD
from ventoy_macos.object import Object
from ventoy_macos.partialproperty import partialproperty

bp = breakpoint


def require_fd(func):
    """Return a decorator for methods that require an open FD."""

    def wrapper(self):
        """Ensure .disk exists and open self.fd if it is not already."""
        if not self.disk:
            raise VentoyMacosError("Cannot write to disk: no .disk attribute.")
        if not (self.fd.is_open or self.fd.id):
            self.fd.open()
        func(self)
    return wrapper


def verify_attr(*attrs):
    """Verify that an attribute is present and not null."""

    def decorator(func):
        """Return wrapper function."""

        def wrapper(self):
            """Ensure .disk exists and open self.fd if it is not already."""
            for attr in attrs:
                value = getattr(self, attr, None)
                if not value:
                    raise VentoyMacosError(
                        f"Unable to write {attr} to disk as the value is not set."
                    )
            func(self)
        return wrapper
    return decorator


class Builder(Object):
    """Bootable USB Builder."""

    PAUSE = 2
    """Seconds to wait."""

    ATTRS = {
        "images_path": None,
        "mbr": None,
        "primary": None,
        "entries": None,
        "backup": None,
        "layout": None,
    }

    _fd: FD = None
    _boot_img: bytes = None
    _core_img: bytes = None
    _disk_img: bytes = None

    def __init__(self, disk: Disk = None, **kwargs):
        """Initialize the object."""
        self.disk = disk
        super().__init__(**kwargs)

    def _get_image_file(self, name: str) -> bytes:
        """Read a image file."""
        attr_name = f"_{name}_img"
        if not getattr(self, attr_name, None):
            if self.images_path:
                path = self.images_path / f"{name}.img"
                if not path.is_file():
                    raise VentoyMacosError(f"No such image file: '{path}'")
                image = path.read_bytes()
                setattr(self, attr_name, image)
        return getattr(self, attr_name)

    def _set_image_file(self, value: bytes, name: str):
        """Set an image file attribute."""
        attr_name = f"_{name}_img"
        setattr(self, attr_name, value)

    boot_img = partialproperty(
        getter=_get_image_file,
        setter=_set_image_file,
        name="boot"
    )

    core_img = partialproperty(
        getter=_get_image_file,
        setter=_set_image_file,
        name="core",
    )

    disk_img = partialproperty(
        getter=_get_image_file,
        setter=_set_image_file,
        name="disk",
    )

    @property
    def fd(self) -> FD:
        """Get the fd object."""
        if not self.disk:
            return
        if not self._fd:
            self._fd = FD(self.disk)
        return self._fd

    def unmount(self):
        """Unmount disk and wait for it to finish."""
        if not self.disk:
            return
        self.disk.unmount()
        sleep(self.PAUSE)

    @require_fd
    def write_init_header(self):
        """Zero first 1MB (protective MBR + GPT header + entries area)."""
        self.fd.write(0, b"\x00" * s2b(2048))

    @require_fd
    def write_init_backup(self):
        """Zero backup GPT area."""
        self.fd.write(
            s2b(self.disk.sectors - 33),
            b"\x00" * s2b(33)
        )

    @verify_attr("mbr")
    @require_fd
    def write_mbr(self):
        """Write protective MBR."""
        self.fd.write(0, self.mbr)

    @verify_attr("primary")
    @require_fd
    def write_primary_header(self):
        """Write primary GPT header (sector 1)."""
        self.fd.write(SECTOR_SIZE, self.primary)

    @verify_attr("entries")
    @require_fd
    def write_entries(self):
        """Write backup GPT entries + header."""
        self.fd.write(s2b(2), self.entries)

    @verify_attr("entries", "backup")
    @require_fd
    def write_backup(self):
        """Write backup GPT."""
        self.fd.write(s2b(self.disk.sectors - 33), self.entries)
        self.fd.write(s2b(self.disk.sectors - 1),  self.backup)

    @verify_attr("boot_img")
    @require_fd
    def write_boot_img(self):
        """Write Ventoy boot.img (446 bytes of BIOS boot code to MBR)."""
        self.fd.patch(0, 0, self.boot_img[:446])

    @require_fd
    def write_gpt_marker(self):
        """Write GPT marker at offset 92."""
        self.fd.patch(0, 92, b"\x22")

    @verify_attr("core_img")
    @require_fd
    def write_core_img(self):
        """Write core.img."""
        core = self.core_img[: s2b(2014)]
        if len(core) % SECTOR_SIZE:
            core += b"\x00" * (SECTOR_SIZE - len(core) % SECTOR_SIZE)
        self.fd.write(s2b(34), core)

    @verify_attr("disk_img", "layout")
    @require_fd
    def write_disk_img(self):
        """Write ventoy.disk.img to partition 2."""
        self.fd.write(s2b(self.layout[1].start), self.disk_img)

    @require_fd
    def write_disk_uuid(self):
        """Write disk UUID at offset 384."""
        self.fd.patch(0, 384, uuid4().bytes)

    @require_fd
    def write_disk_signature(self):
        """Write disk signature at offset 440."""
        self.fd.patch(0, 440, urandom(4))

    @require_fd
    def write_second_gpt_marker(self):
        """Write second GPT marker."""
        self.fd.patch(*b2s(17908), b"\x23")
