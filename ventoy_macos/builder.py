"""Bootable USB Builder."""

from functools import partial
from os import urandom
from time import sleep
from uuid import uuid4

from attr import attr, hasattrs

from ventoy_macos import SECTOR_SIZE, VentoyMacosError
from ventoy_macos.common import b2s, clear, s2b
from ventoy_macos.decorators import _private_setter, require_fd, verify_attr
from ventoy_macos.disk import Disk
from ventoy_macos.disk_image import DiskImage
from ventoy_macos.fd import FD
from ventoy_macos.object import Object
from ventoy_macos.partialproperty import partialproperty

bp = breakpoint


@hasattrs
class Builder(Object):
    """Bootable USB Builder."""

    PAUSE = 2
    """Seconds to wait."""

    ATTRS = {
        "disk": None,
        "gpt": None,
        "images": {},
    }

    _boot_img = None
    _core_img = None
    _disk_img = None

    def __init__(self, disk: Disk = None, **kwargs):
        """Initialize the object."""
        self.disk = disk
        super().__init__(**kwargs)

    def __repr__(self):
        """Builder(disk='device')."""
        text = ""
        if (device := getattr(self.disk, "device", "")):
            text = f"disk='{device}'"

        return f"Builder({text})"

    def _get_from_gpt(self, attr):
        """Get an attribute from .gpt."""
        if not self.gpt:
            return
        return getattr(self.gpt, attr, None)

    mbr = attr("mbr", getter=partial(_get_from_gpt, attr="mbr"))
    primary = attr("primary", getter=partial(_get_from_gpt, attr="primary"))
    entries = attr("entries", getter=partial(_get_from_gpt, attr="entries"))
    backup = attr("backup", getter=partial(_get_from_gpt, attr="backup"))
    layout = attr("layout", getter=partial(_get_from_gpt, attr="layout"))

    def _get_disk_image(self, name) -> DiskImage:
        """Get the appropriate disk image from .images."""
        # get the existing private disk image attribute
        _name = f"_{name}"
        img = getattr(self, _name)

        # get the default image from .images
        # and set the private attribute
        if not img:
            img = self.images.get(name)
            if img:
                setattr(self, _name, img)

        if not img:
            return

        # make sure the value has a value for .data
        if not getattr(img, "data", None):
            raise VentoyMacosError(
                f"Builder: The {name} DiskImage does not have any data. "
                f"({type(img)}) {img}"
            )

        # return the img.data
        return img.data

    boot_img = partialproperty(
        getter=_get_disk_image,
        setter=_private_setter,
        name="boot_img",
    )

    core_img = partialproperty(
        getter=_get_disk_image,
        setter=_private_setter,
        name="core_img",
    )

    disk_img = partialproperty(
        getter=_get_disk_image,
        setter=_private_setter,
        name="disk_img",
    )

    @attr
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
        self.fd.write(0, clear(s2b(2048)))

    @require_fd
    def write_init_backup(self):
        """Zero backup GPT area."""
        self.fd.write(
            s2b(self.disk.sectors - 33),
            clear(s2b(33)),
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
            core += clear((SECTOR_SIZE - len(core) % SECTOR_SIZE))
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
