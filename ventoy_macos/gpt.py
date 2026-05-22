"""Functions related to GPT construction."""

import struct
import uuid
import zlib

from ventoy_macos import SECTOR_SIZE

GPT_BASIC_DATA_GUID = uuid.UUID("EBD0A0A2-B9E5-4433-87C0-68B6B72699C7")

bp = breakpoint


def make_entries(e1, e2):
    """Combine e1 and e2."""
    return e1 + e2 + b"\x00" * (128 * 128 - 256)


def make_crc(data):
    """Make crc."""
    return zlib.crc32(data) & 0xFFFFFFFF


def uuid_to_mixed_endian(u):
    """Convert a UUID to mixed endian."""
    b = u.bytes
    return b[3::-1] + b[5:3:-1] + b[7:5:-1] + b[8:16]


def make_gpt_entry(type_guid, unique_guid, start, end, attrs, name):
    """Make a GPT entry."""
    t = uuid_to_mixed_endian(type_guid)
    u = uuid_to_mixed_endian(unique_guid)
    n = name.encode("utf-16-le")
    n += b"\x00" * (72 - len(n))
    return struct.pack("<16s16sQQQ72s", t, u, start, end, attrs, n)


def make_gpt_header(params):
    """Make GPT header."""
    data = struct.pack(
        "<8sIIIIQQQQ16sQIII",
        b"EFI PART",
        0x00010000,
        92,
        0,  # CRC placeholder
        0,
        params["my_lba"],
        params["alt_lba"],
        params["first_usable"],
        params["last_usable"],
        uuid_to_mixed_endian(params["disk_guid"]),
        params["entry_start"],
        params["num_entries"],
        params["entry_size"],
        params["entries_crc"],
    )
    crc = make_crc(data)
    data = data[:16] + struct.pack("<I", crc) + data[20:]
    return data + b"\x00" * (SECTOR_SIZE - len(data))


def build_gpt(disk_sectors, layout):
    """Build complete GPT structures."""
    disk_guid = uuid.uuid4()

    e1 = make_gpt_entry(
        GPT_BASIC_DATA_GUID,
        uuid.uuid4(),
        layout[0].start,
        layout[0].end,
        0,
        "Ventoy",
    )
    e2 = make_gpt_entry(
        GPT_BASIC_DATA_GUID,
        uuid.uuid4(),
        layout[1].start,
        layout[1].end,
        0,
        "VTOYEFI",
    )
    entries = make_entries(e1, e2)
    entries_crc = make_crc(entries)

    common = {
        "disk_guid": disk_guid,
        "first_usable": 2048,
        "last_usable": disk_sectors - 34,
        "num_entries": 128,
        "entry_size": 128,
        "entries_crc": entries_crc,
    }

    primary = make_gpt_header(
        {**common, "my_lba": 1, "alt_lba": disk_sectors - 1, "entry_start": 2}
    )
    backup = make_gpt_header(
        {
            **common,
            "my_lba": disk_sectors - 1,
            "alt_lba": 1,
            "entry_start": disk_sectors - 33,
        }
    )

    # Protective MBR
    mbr = bytearray(512)
    mbr[446:447] = b"\x00"
    mbr[448] = 0x02
    mbr[450] = 0xEE
    mbr[451] = mbr[452] = mbr[453] = 0xFF
    struct.pack_into("<I", mbr, 454, 1)
    struct.pack_into("<I", mbr, 458, min(disk_sectors - 1, 0xFFFFFFFF))
    mbr[510] = 0x55
    mbr[511] = 0xAA

    return bytes(mbr), primary, entries, backup
