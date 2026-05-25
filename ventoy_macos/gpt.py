"""Functions related to GUID Partition Table (GPT) construction."""

import struct
import uuid
import zlib
from functools import cached_property, partial

from attr import attr, hasattrs

from ventoy_macos import SECTOR_SIZE, VentoyMacosError
from ventoy_macos.common import clear
from ventoy_macos.decorators import _get_cached_uuid
from ventoy_macos.object import Object

bp = breakpoint


@hasattrs
class GPT(Object):
    """Functions related to GUID Partition Table (GPT) construction."""

    # partition type
    GPT_BASIC_DATA_GUID = uuid.UUID("EBD0A0A2-B9E5-4433-87C0-68B6B72699C7")

    PARTITION_START_LBA = 2048

    ENTRY_SIZE = 128

    ENTRY_COUNT = 128

    def __init__(self, sectors: int = None, layout: list = [], **kwargs):
        """Initialize."""
        self.sectors = sectors
        self.layout = layout

        super().__init__(**kwargs)

    guid = attr("guid", getter=partial(_get_cached_uuid, name="guid"))
    e1_uuid = attr("e1_uuid", getter=partial(_get_cached_uuid, name="e1_uuid"))
    e2_uuid = attr("e2_uuid", getter=partial(_get_cached_uuid, name="e2_uuid"))

    def to_le(self, u: uuid.UUID) -> bytes:
        """Convert a UUID to little endian.

        (Reverse the byte order.)
        """
        b = u.bytes
        return b[3::-1] + b[5:3:-1] + b[7:5:-1] + b[8:16]

    @property
    def last_usable(self) -> int:
        """Return the last usable LBA (for partitions)."""
        if not self.sectors:
            raise VentoyMacosError("GPT.last_usable: .sectors not defined")
        return self.sectors - 34

    def make_checksum(self, data: bytes) -> bytes:
        """Generate CRC-32 checksum."""
        return zlib.crc32(data) & 0xFFFFFFFF

    @property
    def mbr(self) -> bytes:
        """Make protective MBR."""
        if not self.sectors:
            raise VentoyMacosError("GPT.mbr: .sectors not defined")
        mbr = bytearray(512)
        mbr[446:447] = b"\x00"
        mbr[448] = 0x02
        mbr[450] = 0xEE
        mbr[451] = mbr[452] = mbr[453] = 0xFF
        struct.pack_into("<I", mbr, 454, 1)
        struct.pack_into("<I", mbr, 458, min(self.sectors - 1, 0xFFFFFFFF))
        mbr[510] = 0x55
        mbr[511] = 0xAA
        return mbr

    @cached_property
    def e1(self) -> bytes:
        """Return the entry for partition 1."""
        if not self.layout:
            raise VentoyMacosError("GPT.e1: .layout not defined")

        return self.make_entry(
            self.layout[0].start,
            self.layout[0].end,
            "Ventoy",
            self.e1_uuid,
        )

    @cached_property
    def e2(self) -> bytes:
        """Return the entry for partition 2."""
        if not self.layout:
            raise VentoyMacosError("GPT.e2: .layout not defined")

        return self.make_entry(
            self.layout[1].start,
            self.layout[1].end,
            "VTOYEFI",
            self.e2_uuid,
        )

    @cached_property
    def entries(self):
        """Return the entries."""
        if not (self.e1 and self.e2):
            raise VentoyMacosError("GPT.entries: .e1 and .e2 must be defined")
        return self.e1 + self.e2 + clear((self.ENTRY_SIZE * self.ENTRY_COUNT) - 256)

    @cached_property
    def primary(self) -> bytes:
        """Return the primary header."""
        if not self.sectors:
            raise VentoyMacosError("GPT.primary: .sectors not defined")
        return self.make_header(
            lba=1,
            alt_lba=self.sectors - 1,
            entry_start=2,
        )

    @cached_property
    def backup(self) -> bytes:
        """Return the backup header."""
        if not self.sectors:
            raise VentoyMacosError("GPT.backup: .sectors not defined")
        return self.make_header(
            lba=self.sectors - 1,
            alt_lba=1,
            entry_start=self.sectors - 33,
        )

    @cached_property
    def entries_crc(self) -> int:
        """Return the CRC-32 checksum for self.entries."""
        return self.make_checksum(self.entries)

    def make_entry(
        self,
        start: int,
        end: int,
        name: str,
        id: uuid.UUID,
        attrs: bytes = 0,
    ) -> bytes:
        """Make a GPT entry."""
        n = name.encode("utf-16-le")

        entry = struct.pack(
            "<16s16sQQQ72s",
            self.to_le(self.GPT_BASIC_DATA_GUID),
            self.to_le(id),
            start,
            end,
            attrs,
            clear(72, n),
        )
        return entry

    def make_header(
        self,
        lba: int,
        alt_lba: int,
        entry_start: int,
    ):
        """Make GPT header."""
        data = struct.pack(
            "<8sIIIIQQQQ16sQIII",
            b"EFI PART",                  # signature
            0x00010000,                   # revision number
            92,                           # header size
            0,                            # CRC placeholder
            0,                            # reserved, always 0
            lba,                          # this header's LBA
            alt_lba,                      # other header LBA
            self.PARTITION_START_LBA,     # partition LBA start
            self.last_usable,             # partition LBA end
            self.to_le(self.guid),
            entry_start,                  # entries start LBA
            self.ENTRY_COUNT,
            self.ENTRY_SIZE,
            self.entries_crc,             # entries checksum
        )

        crc = self.make_checksum(data)
        data = data[:16] + struct.pack("<I", crc) + data[20:]
        return clear(SECTOR_SIZE, data)
