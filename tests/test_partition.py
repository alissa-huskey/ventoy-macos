from ventoy_macos.partition import Partition

bp = breakpoint


def test_partition():
    assert Partition()


def test_partition_sectors():
    part = Partition(start=2048, end=124934430)
    assert part.sectors == 124932383


def test_partition_mb():
    ...


def test_partition_():
    ...
