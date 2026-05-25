from subprocess import CompletedProcess

import pytest

from ventoy_macos.common import b2s, clear, run, s2b, s2g, s2m, size_text

bp = breakpoint


def test_run():
    result = run(["echo", "hello"])

    assert isinstance(result, CompletedProcess)
    assert result.returncode == 0
    assert result.stdout == "hello\n"


def test_s2b():
    size = s2b(1)

    assert size == 512


def test_b2s():
    sectors = b2s(1152)
    assert sectors == (2, 128)


def test_s2g():
    assert s2g(10485672) == 4.999958038330078


def test_s2m():
    assert s2m(65536) == 31.25


@pytest.mark.parametrize(["sectors", "expected"], [
    (10485672, "5.0 GiB"),
    (65536, "31 MiB"),
])
def test_size_text(sectors, expected):
    assert size_text(sectors) == expected


@pytest.mark.parametrize(["args", "expected"], [
    ([20], b"\x00" * 20),
    ([20, b"prefix"], b"prefix" + (b"\x00" * 14)),
])
def test_clear(args, expected):
    result = clear(*args)
    assert result == expected


#  def test_():
#      """
#      GIVEN: ...
#      WHEN: ...
#      THEN: ...
#      """
