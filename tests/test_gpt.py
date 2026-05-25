"""GPT tests.

The results in most of these tests are binary values that are both inscrutable
and quite large.

When I ported this from the original `ventoy_macos_install.py` script, I ran
the functions with a set of consistent parameters and stored the results in
`tests/data.py`, thereby gathering a set of (presumbaly) know good fixture data
that is out of the way.
"""

from uuid import UUID

import pytest

from tests import data
from ventoy_macos.gpt import GPT

bp = breakpoint


# stores the UUIDS for mock uuid4
UUIDS = []


def mock_uuid4():
    """Return a UUID.

    Remove from the beginning of UUIDS. This ensures that we have a consistent
    series of test UUIDs.
    """
    return UUIDS.pop(0)


@pytest.fixture
def gpt(sectors_64g, planned_layout) -> GPT:
    """Return a GPT object."""
    return GPT(
        sectors_64g,
        planned_layout,
        guid=data.diskuuid,
        e1_uuid=data.e1uuid,
        e2_uuid=data.e2uuid,
    )


def test_gpt():
    assert GPT()


def test_gpt_to_le():
    expected = b'\xa2\xa0\xd0\xeb\xe5\xb93D\x87\xc0h\xb6\xb7&\x99\xc7'
    gpt = GPT()
    assert gpt.to_le(GPT.GPT_BASIC_DATA_GUID) == expected


def test_gpt_make_checksum():
    gpt = GPT()
    assert gpt.make_checksum(data.entries) == data.entries_crc


def test_gpt_build(monkeypatch):
    guid = UUID("3b7b067c-faea-402b-93f8-df39b0dba248")
    with monkeypatch.context() as m:
        m.setattr("uuid.uuid4", lambda: guid)

        gpt = GPT()
        assert gpt.guid == guid


def test_gpt_last_usable(sectors_64g):
    gpt = GPT(sectors=sectors_64g)
    assert gpt.last_usable == sectors_64g - 34


def test_gpt_mbr(sectors_64g):
    gpt = GPT(sectors=sectors_64g)
    assert gpt.mbr == data.mbr


def test_gpt_make_entry(monkeypatch, planned_layout):
    gpt = GPT(layout=planned_layout)
    entry = gpt.make_entry(
        planned_layout[0].start,
        planned_layout[0].end,
        "Ventoy",
        data.e1uuid,
    )

    assert entry == data.entry1


@pytest.mark.parametrize(["number", "uuid", "entry"], [
    (1, data.e1uuid, data.entry1),
    (2, data.e2uuid, data.entry2),
])
def test_gpt_entry(monkeypatch, gpt, number, uuid, entry):
    with monkeypatch.context() as m:
        m.setattr("uuid.uuid4", lambda: uuid)
        assert getattr(gpt, f"e{number}") == entry


def test_gpt_make_header(gpt, sectors_64g):
    result = gpt.make_header(
        lba=1,
        alt_lba=sectors_64g - 1,
        entry_start=2,
    )

    assert gpt.entries_crc == data.entries_crc
    assert result == data.header


def test_gpt_entries(gpt, monkeypatch):
    with monkeypatch.context() as m:
        global UUIDS
        UUIDS = [data.e1uuid, data.e2uuid]
        m.setattr("uuid.uuid4", mock_uuid4)

        assert gpt.entries == data.entries


def test_gpt_entries_crc(monkeypatch, gpt):
    with monkeypatch.context() as m:
        global UUIDS
        UUIDS = [data.e1uuid, data.e2uuid]
        m.setattr("uuid.uuid4", mock_uuid4)
        assert gpt.entries_crc == data.entries_crc


def test_gpt_primary(gpt):
    assert gpt.primary == data.header


def test_gpt_backup(gpt):
    assert gpt.backup == data.backup


#  def test_():
#      ...
