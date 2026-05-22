from ventoy_macos.partition import Partition

bp = breakpoint


def test_partition():
    assert Partition()


def test_partition_sectors_start_end():
    part = Partition(start=2048, end=124934430)
    assert part.sectors == 124932383


def test_partition_sectors_bytes():
    part = Partition(bytes=8173993984)
    assert part.sectors == 15964832


#  def test_partition_():
#      ...
