"""GPT construction."""


def uuid_to_mixed_endian(u):
    b = u.bytes
    return b[3::-1] + b[5:3:-1] + b[7:5:-1] + b[8:16]


def make_gpt_entry(type_guid, unique_guid, start, end, attrs, name):
    t = uuid_to_mixed_endian(type_guid)
    u = uuid_to_mixed_endian(unique_guid)
    n = name.encode("utf-16-le")
    n += b"\x00" * (72 - len(n))
    return struct.pack("<16s16sQQQ72s", t, u, start, end, attrs, n)


def make_gpt_header(params):
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
    crc = zlib.crc32(data) & 0xFFFFFFFF
    data = data[:16] + struct.pack("<I", crc) + data[20:]
    return data + b"\x00" * (SECTOR_SIZE - len(data))


def build_gpt(disk_sectors, layout):
    """Build complete GPT structures."""
    disk_guid = uuid.uuid4()

    e1 = make_gpt_entry(
        GPT_BASIC_DATA_GUID,
        uuid.uuid4(),
        layout["part1_start"],
        layout["part1_end"],
        0,
        "Ventoy",
    )
    e2 = make_gpt_entry(
        GPT_BASIC_DATA_GUID,
        uuid.uuid4(),
        layout["part2_start"],
        layout["part2_end"],
        0,
        "VTOYEFI",
    )
    entries = e1 + e2 + b"\x00" * (128 * 128 - 256)
    entries_crc = zlib.crc32(entries) & 0xFFFFFFFF

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


def patch_sector(fd, sector_lba, offset, data):
    """Read-modify-write a sector to patch sub-sector bytes."""
    os.lseek(fd, sector_lba * SECTOR_SIZE, os.SEEK_SET)
    sector = bytearray(os.read(fd, SECTOR_SIZE))
    sector[offset : offset + len(data)] = data
    os.lseek(fd, sector_lba * SECTOR_SIZE, os.SEEK_SET)
    os.write(fd, bytes(sector))


def write_to_disk(
    raw_device,
    disk,
    disk_sectors,
    layout,
    mbr,
    primary,
    entries,
    backup,
    boot_img_path,
    core_img_path,
    disk_img_path,
):
    """Write GPT and Ventoy boot code to the disk."""

    boot_img = open(boot_img_path, "rb").read()
    core_img = open(core_img_path, "rb").read()
    disk_img = open(disk_img_path, "rb").read()

    # Unmount
    print("Unmounting disk...")
    run(["diskutil", "unmountDisk", "force", disk], check=False)
    time.sleep(2)

    print("Writing to disk...")
    fd = os.open(raw_device, os.O_RDWR)
    try:
        # Zero first 1MB (protective MBR + GPT header + entries area)
        print("  Zeroing first 1MB...")
        os.lseek(fd, 0, os.SEEK_SET)
        os.write(fd, b"\x00" * (2048 * SECTOR_SIZE))

        # Zero backup GPT area
        print("  Zeroing backup GPT area...")
        os.lseek(fd, (disk_sectors - 33) * SECTOR_SIZE, os.SEEK_SET)
        os.write(fd, b"\x00" * (33 * SECTOR_SIZE))

        # Write protective MBR
        print("  Writing protective MBR...")
        os.lseek(fd, 0, os.SEEK_SET)
        os.write(fd, mbr)

        # Write primary GPT header (sector 1)
        print("  Writing primary GPT header...")
        os.lseek(fd, SECTOR_SIZE, os.SEEK_SET)
        os.write(fd, primary)

        # Write primary GPT entries (sectors 2-33)
        print("  Writing GPT entries...")
        os.lseek(fd, 2 * SECTOR_SIZE, os.SEEK_SET)
        os.write(fd, entries)

        # Write backup GPT entries + header
        print("  Writing backup GPT...")
        os.lseek(fd, (disk_sectors - 33) * SECTOR_SIZE, os.SEEK_SET)
        os.write(fd, entries)
        os.lseek(fd, (disk_sectors - 1) * SECTOR_SIZE, os.SEEK_SET)
        os.write(fd, backup)

        # Write Ventoy boot.img (446 bytes of BIOS boot code to MBR)
        print("  Writing Ventoy boot.img...")
        patch_sector(fd, 0, 0, boot_img[:446])

        # GPT marker at offset 92
        patch_sector(fd, 0, 92, b"\x22")

        # Write core.img to sectors 34-2047 (GPT gap area)
        print("  Writing core.img...")
        os.lseek(fd, 34 * SECTOR_SIZE, os.SEEK_SET)
        core = core_img[: 2014 * SECTOR_SIZE]
        if len(core) % SECTOR_SIZE:
            core += b"\x00" * (SECTOR_SIZE - len(core) % SECTOR_SIZE)
        os.write(fd, core)

        # Second GPT marker at offset 17908
        patch_sector(fd, 17908 // SECTOR_SIZE, 17908 % SECTOR_SIZE, b"\x23")

        # Write ventoy.disk.img to partition 2
        part2_start = layout["part2_start"]
        print(f"  Writing ventoy.disk.img at sector {part2_start}...")
        os.lseek(fd, part2_start * SECTOR_SIZE, os.SEEK_SET)
        os.write(fd, disk_img)

        # Disk UUID at offset 384
        patch_sector(fd, 0, 384, uuid.uuid4().bytes)

        # Disk signature at offset 440
        patch_sector(fd, 0, 440, os.urandom(4))

        os.fsync(fd)
        print("  All writes complete.")
    finally:
        os.close(fd)


def format_partition1(disk, fs_type="exfat"):
    """Format partition 1 with the specified filesystem."""
    part1 = f"{disk}s1"

    print(f"\nWaiting for macOS to detect partitions...")
    time.sleep(3)

    run(["diskutil", "unmountDisk", "force", disk], check=False)
    time.sleep(1)

    if fs_type == "exfat":
        print(f"Formatting {part1} as exFAT...")
        result = run(["newfs_exfat", "-v", "Ventoy", part1], check=False)
        if result.returncode != 0:
            print("  newfs_exfat failed, trying diskutil...")
            run(["diskutil", "eraseVolume", "ExFAT", "Ventoy", part1])
    else:
        # NTFS is not natively supported for formatting on macOS
        # but Ventoy data partition can remain unformatted and be formatted elsewhere
        print(f"Warning: macOS cannot natively format NTFS.")
        print(f"Formatting {part1} as exFAT instead (readable on Windows/Linux/macOS).")
        result = run(["newfs_exfat", "-v", "Ventoy", part1], check=False)
        if result.returncode != 0:
            run(["diskutil", "eraseVolume", "ExFAT", "Ventoy", part1])


def verify(disk):
    """Print final disk layout and verify partition 1 offset."""
    time.sleep(2)
    run(["diskutil", "mountDisk", disk], check=False)
    time.sleep(1)

    print("\n" + "=" * 50)
    print("Disk layout:")
    print("=" * 50)
    run(["diskutil", "list", disk], capture=False)

    result = run(["diskutil", "info", f"{disk}s1"])
    for line in result.stdout.split("\n"):
        if "Offset" in line:
            print(f"\n{line.strip()}")
            if "2048" in line:
                print("  -> Correct! Partition 1 starts at sector 2048 (1MB)")
            else:
                print("  -> WARNING: Partition 1 does not start at sector 2048!")
