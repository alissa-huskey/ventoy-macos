Writes
======

> The things that get written to disk, their positions and sizes. So I can
> figure out how to group them in buffers.

| Start   | Size       | Contents       | Type            | Group       | Notes                        |
|---------|------------|----------------|-----------------|-------------|------------------------------|
| 0       | 512        | PMBR           | PMBR            | Init        | -                            |
| 0       | 512 (446)  | boot.img       | PMBR            | PMBR        | -                            |
| 92      | 1          | GPT Marker     | Partition Table | TableBody   | -                            |
| 348     | 16         | Disk UUID      | Partition Table | TableBody   | -                            |
| 440     | 8          | Disk Signature | Partition Table | TableBody   | -                            |
| 512     | 512        | Primary Header | Partition Table | TableHeader | -                            |
| 1024    | 16,384     | Entries        | Partition Table | TableBody   | -                            |
| 2048    | 33,554,432 | disk.img       | Data Disk Image | Images      | -                            |
| 17,408  | 1,031,168  | core.img       | Data Disk Image | Images      | -                            |
| 17,908  | 1          | GPT Marker     | Partition Table | Images      | This position can't be right |
| -17,408 | 16,384     | Backup Entries | Partition Table | TableBackup | -                            |
| -512    | 512        | Backup Header  | Partition Table | TableBackup | -                            |
| -       | -          | -              | -               | -           | -                            |


> The actual groupings.
>
> Note that the size is not neccessarily the sum of its consituant parts. It
> may include space between the end of one entry and the next.


| Order | Group       | Size       | Start LBA | Notes                                                                     |
|-------|-------------|------------|-----------|---------------------------------------------------------------------------|
| 1     | Images      | 33,000,000 | 2048      | -                                                                         |
| 2     | TableBody   | 17,316     | 92        | This overlaps with TableHeader, but it's ok because that's written later. |
| 3     | TableBackup | 17,408     | -17,408   | -                                                                         |
| 4     | PMBR        | 512        | 0         | -                                                                         |
| 5     | TableHeader | 512 (92)   | 512       | -                                                                         |
| -     | -           | -          | -         | -                                                                         |
