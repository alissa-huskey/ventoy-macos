import pytest
from rich.console import Console
from rich.rule import Rule as RichRule  # noqa F401

from tests import Stub
from ventoy_macos.rule import Rule

bp = breakpoint


def render(rule: Rule):
    """Return the text parts of a rendered rule."""
    console = Console(width=100)
    parts = [t.text for t in console.render(rule)]
    if parts[-1] == "\n":
        parts.pop()
    return parts


def test_rule_no_text():
    rule = Rule()
    parts = render(rule)
    text = "".join(parts)

    assert len(parts) == 1
    assert len(text) == 100


@pytest.mark.parametrize(["params"], [
    [Stub(
        kwargs={"width": 50},
        width=50,
        parts=3,
        align="center",
        title_idx=1,
        title=" hello ",
    )],
    [Stub(
        kwargs={"align": "left"},
        width=100,
        parts=2,
        align="left",
        title_idx=0,
        title="hello ",
    )],
    [Stub(
        kwargs={"align": "right"},
        width=100,
        parts=2,
        align="right",
        title_idx=-1,
        title=" hello",
    )],
    [Stub(
        kwargs={},
        width=100,
        parts=3,
        align="center",
        title_idx=1,
        title=" hello ",
    )],
    [Stub(
        kwargs={"align": "left", "width": 50},
        width=50,
        parts=2,
        align="left",
        title_idx=0,
        title="hello ",
    )],
    [Stub(
        kwargs={"align": "right", "width": 50},
        width=50,
        parts=2,
        align="right",
        title_idx=-1,
        title=" hello",
    )],
    [Stub(
        kwargs={"align": "left", "width": 50, "end_size": 2},
        width=50,
        parts=3,
        align="left",
        title_idx=1,
        title=" hello ",
        end_idx=0,
    )],
    [Stub(
        kwargs={"align": "right", "width": 50, "end_size": 2},
        width=50,
        parts=3,
        align="right",
        title_idx=1,
        title=" hello ",
        end_idx=-1,
    )],
    #  [Stub(
    #      kwargs={},
    #      width=-,
    #      parts=-,
    #      align="-",
    #      title_idx=-,
    #      title="-",
    #  ),
])
def test_rule_params(params):
    """
    WHEN: A Rule object is created with a particular set of keyword arguments
    THEN: it should be the correct total length
    AND: it should have the correct number of spans
    AND: the title should be in the right position and have the right number of
         spaces around it
    """
    rule = Rule("hello", **params.kwargs)
    spans = render(rule)
    text = "".join(spans)

    assert rule.align == params.align
    assert len(text) == params.width
    assert len(spans) == params.parts
    assert spans[params.title_idx] == params.title
    assert not params.end_idx or len(spans[params.end_idx]) == params.kwargs["end_size"]
