from subprocess import CompletedProcess

from ventoy_macos.common import b2s, run, s2b

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


#  def test_():
#      """
#      GIVEN: ...
#      WHEN: ...
#      THEN: ...
#      """
