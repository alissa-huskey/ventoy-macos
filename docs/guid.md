GUID Partition Table
====================

Notes on the GUID Partition Table (GPT) partition table layout standard.

Partition Table
---------------

The partition table describes the layout of the partitions on the disk. In GPT, it consists of:

### Protective MBR

A section of blocks in the same space reserved for an MBR which identifies the
partition scheme as GPT and prevents MBR-based utiities don't understand GPT
from attempting write operations.

### Headers

Describes the partition table.

| Offset | Size | Contents                                   |
|--------|------|--------------------------------------------|
| 0      | 8    | Signature (LE)                             |
| 8      | 4    | Revision number                            |
| 12     | 12   | Header size (LE)                           |
| 16     | 16   | CRC-32 checksum (LE)                       |
| 20     | 4    | Reserved, 0                                |
| 24     | 8    | Current LBA (location of this header copy) |
| 32     | 8    | Backup LBA (location of other header copy) |
| 40     | 8    | First usable partition LBA                 |
| 48     | 8    | Last usable partition LBA                  |
| 56     | 16   | Disk UUID (LE)                             |
| 72     | 8    | Start LBA of entries                       |
| 80     | 4    | Number of entries                          |
| 84     | 4    | Entry size                                 |
| 88     | 4    | Entries CRC-32 checksum (LE)               |
| 92     | *    | `\x00` until the end of the block          |

### Entries

Describes each partition on the drive.

| Size | Contents            |
|------|---------------------|
| 16   | Partition Type GUID |
| 16   | Partition GUID      |
| 8    | Start (LE)          |
| 8    | End (LE, inclusive) |
| 8    | Attribute flags     |
| 72   | Partition name      |

Glossary
--------

* Partition Scheme: a standard (such as GPT) for the layout of the partition
    table.
* Partition Table, Partition Map: the information about partitions' locations
    and sizes on a disk that the operation system reads first.
* Logical Block Address (LBA): a system for addressing fixed-size blocks
    (sectors) on a storage device (regardless of physical block size). Also
    used to refer to the location (address or base address) of a particular
    block on a disk, for example `LBA 0`, `LBA 1`, etc.
* Sector, Block: a fixed-sized sequence of bytes that make up an addressed
    section of data on a disk, usually read and written a block at a time.
* Partition: a section of space on a disk that can be seen as its own "logical"
  disk.
* Unique Identifier (UUID): a 128-bit (16 byte) identifier, typically displayed in five
  groups separated by hyphens (`xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`).
* Globally Unique Identifier (GUID): Microsoft's UUID variant.
* Primary Partition: a partition that contains one file system
* Partition Type, Partition ID: A byte value in the partition table that
    specifies the file system or to flag special access methods.
* Edian: the order in which bytes are addressed, either or Big-Edian
    (BE): left to right, or Little-Edian (LE): right to left.
* Cyclic Redundancy Check (CRC): an algorithm to generate checksum data used to
    verify data integrity. One common CRC algorithmis CRC-32. May also refer to
    the checksum data.
* Master Boot Record (MBR): a partitioning scheme. Also refers to the partition
  table in that scheme, which is located at `LBA 0`.
* Partion Entry, Partition Entry Array: a section of bytes in the GPT partition
  table that describes each partition.
