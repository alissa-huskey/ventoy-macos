from uuid import UUID

import pytest

from tests import data
from ventoy_macos.gpt import (GPT_BASIC_DATA_GUID, build_gpt, make_crc,
                              make_entries, make_gpt_entry, make_gpt_header,
                              uuid_to_mixed_endian)

bp = breakpoint


UUIDS = [
    UUID('a8ebd70f-46b8-4036-904f-fd688267cc71'),
    UUID('2d5db76c-afcc-4c3f-95e4-f861d5eee2db'),
    UUID('8a4ec570-5c41-4302-9c54-293b84268437'),
    UUID('2f51088b-0a47-4230-9e42-f2de6b7dfc1e'),
]


def uuid4():
    """Return a UUID.

    This ensures that we have a static list of UUIDs, so test results are not
    random.
    """
    return UUIDS.pop(0)


@pytest.fixture
def crc():
    """Return the entries CRC."""
    return 337916807


@pytest.fixture
def header():
    """Return a GPT header."""
    return data.header


def test_uuid_to_mixed_endian():
    mixed = uuid_to_mixed_endian(GPT_BASIC_DATA_GUID)
    assert mixed == b'\xa2\xa0\xd0\xeb\xe5\xb93D\x87\xc0h\xb6\xb7&\x99\xc7'


def test_make_gpt_entry(planned_layout):
    entry = make_gpt_entry(
        GPT_BASIC_DATA_GUID,
        UUID('1894a02d-923e-4c79-b61f-d7f6dc2578ad'),
        planned_layout["part1_start"],
        planned_layout["part1_end"],
        0,
        "Ventoy",
    )

    assert entry == data.entry1


def test_make_entries():
    result = make_entries(data.entry1, data.entry2)
    assert result == data.entries


def test_make_crc(crc):
    result = make_crc(data.entries)
    assert result == crc


def test_make_gpt_header(planned_layout, crc, header):
    disk_guid = UUID('62b5b82a-e930-4eb1-9aae-ba8b8d8d7de7')
    disk_sectors = 125000000

    params = {
        "disk_guid": disk_guid,
        "first_usable": 2048,
        "last_usable": disk_sectors - 34,
        "num_entries": 128,
        "entry_size": 128,
        "entries_crc": crc,
        "my_lba": 1,
        "alt_lba": disk_sectors - 1,
        "entry_start": 2,
    }

    result = make_gpt_header(params)
    assert result == header


def test_build_gpt(monkeypatch, sectors_64g, planned_layout):
    with monkeypatch.context() as m:
        m.setattr("uuid.uuid4", uuid4)
        result = build_gpt(sectors_64g, planned_layout)

        assert result == (data.mbr, data.primary, data.build_entries, data.backup)


#  def test_():
#      ...
