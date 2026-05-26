"""Bootable USB Builder."""

from functools import cached_property, partial
from os import urandom
from time import sleep, time

from attr import attr, hasattrs
from loguru import logger

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
        "path": None,
    }

    SAVE_DATA: bool = False
    """Enable/disable saving large data chunks to workdir/data."""

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

    def store_data(self, name: str, value: bytes):
        """Save a copy of value to the workdir/data."""
        if not (self.SAVE_DATA and self.path):
            return
        path = self.path / "data"
        name = name.lower().replace(" ", "-")
        file = path / f"{self.ts}-{name}"
        file.write_bytes(value)

    def log_write(
        self,
        name: str,
        position: int,
        value: bytes,
        length: int = None,
    ):
        """Write a log message about a write."""
        length = length or len(value)

        limit = 100
        if length > limit:
            self.store_data(name, value)
            value = value[:limit] + b"..."

        logger.info(f"Writing {name} to disk @ {position} ({length}): {value!r}")

    @cached_property
    def signature(self) -> bytes:
        """Return a random signature."""
        return urandom(4)

    @cached_property
    def ts(self):
        """Return a timestamp."""
        return int(time())

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
        logger.info(f"Unmounting disk: {self.disk.device}")
        self.disk.unmount()
        sleep(self.PAUSE)

    @require_fd
    def init(self):
        """Zero first 1MB and the backup header location.

        Puts the drive in a state where it will be recognizable by operating
        systems as invalid. If the install fails, this is preferable to having
        a half-installed drive, which an operating system may not know what to
        do with. A obviously invalid drive can be recovered by
        erasing/reformatting.

        Upon successful completion of all writes, the drive will be in a valid
        state.
        """
        self.write_init_header()
        self.write_init_backup()
        self.fd.save()

    def write(self, what: str, position: int, data: bytes, value=None):
        """Log and perform a write to disk.

        Arguments:
            what (str): task title to log
            position (int): position (bytes) on disk to start the write
            data (bytes): data to write to disk
            value (optional): value to log, if different than data
        """
        value = value or data
        self.log_write(what, position, value, len(data))
        self.fd.write(position, data)

    @require_fd
    def write_init_header(self):
        """Zero first 1MB (protective MBR + GPT header + entries area)."""
        self.write("Zeros to First 1MB", 0, clear(s2b(2048)))

    @require_fd
    def write_init_backup(self):
        """Zero backup GPT area."""
        self.write(
            "Zeros to GPT area",
            s2b(self.disk.sectors - 33),
            clear(s2b(33)),
        )

    @verify_attr("mbr")
    @require_fd
    def write_mbr(self):
        """Write protective MBR."""
        self.write("PMBR", 0, self.mbr)

    @verify_attr("primary")
    @require_fd
    def write_primary_header(self):
        """Write primary GPT header (sector 1)."""
        self.write("Primary Header", SECTOR_SIZE, self.primary)

    @verify_attr("entries")
    @require_fd
    def write_entries(self):
        """Write backup GPT entries + header."""
        self.write("Entries", s2b(2), self.entries)

    @verify_attr("entries", "backup")
    @require_fd
    def write_backup(self):
        """Write backup GPT."""
        self.write("Backup Entries", s2b(self.disk.sectors - 33), self.entries)
        self.write("Backup Headers", s2b(self.disk.sectors - 1), self.backup)

    @verify_attr("boot_img")
    @require_fd
    def write_boot_img(self):
        """Write Ventoy boot.img (446 bytes of BIOS boot code to MBR)."""
        self.log_write("boot.img", 0, self.boot_img[:446])

    @require_fd
    def write_gpt_marker(self):
        """Write GPT marker at offset 92."""
        self.log_write("GPT Marker", 92, b"\x22")
        self.fd.patch(0, 92, b"\x22")

    @verify_attr("core_img")
    @require_fd
    def write_core_img(self):
        """Write core.img."""
        core = self.core_img[: s2b(2014)]

        # I dont understand why this is here
        # core should always s2b(2014)
        # and s2b(2014) % SECTOR_SIZE == 0
        if len(core) % SECTOR_SIZE:
            core += clear((SECTOR_SIZE - len(core) % SECTOR_SIZE))

        self.write("core.img", s2b(34), core)

    @verify_attr("disk_img", "layout")
    @require_fd
    def write_disk_img(self):
        """Write ventoy.disk.img to partition 2."""
        self.write("ventoy.disk.img", s2b(self.layout[1].start), self.disk_img)

    @require_fd
    def write_disk_uuid(self):
        """Write disk UUID at offset 384."""
        value = self.gpt.guid

        self.log_write("Disk UUID", 384, value, length=len(value.bytes))
        self.fd.patch(0, 384, value.bytes)

    @require_fd
    def write_disk_signature(self):
        """Write disk signature at offset 440."""
        self.log_write("Disk Signature", 440, self.signature)
        self.fd.patch(0, 440, self.signature)

    @require_fd
    def write_second_gpt_marker(self):
        """Write second GPT marker."""
        value = b"\x23"
        pos = b2s(17908)
        self.log_write("Second GPT Marker", 17908, value)
        self.fd.patch(*pos, value)
