from subprocess import CompletedProcess

from ventoy_macos.common import has, run

bp = breakpoint


def test_run():
    result = run(["echo", "hello"])

    assert isinstance(result, CompletedProcess)
    assert result.returncode == 0
    assert result.stdout == "hello\n"


def test_has():
    assert has("xxx") is False
    assert has("echo") is True

#  def test_():
#      """
#      GIVEN: ...
#      WHEN: ...
#      THEN: ...
#      """
