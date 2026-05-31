from string import Template

import pytest
from rich.prompt import Prompt as RichPrompt

from ventoy_macos import Abort
from ventoy_macos.prompt import Prompt

bp = breakpoint


@pytest.fixture
def input_mock(pop_responses):
    """Return a function to mock rich prompt get_input."""
    def mock(responses):
        return pop_responses(responses, lambda *a, **kw: print(a[2]))
    return mock


def test_prompt():
    prompt = Prompt()
    assert prompt


def test_prompt_choices():
    prompt = Prompt(choices="abc")
    assert prompt.choices == ["a", "b", "c"]


def test_prompt_hidden():
    prompt = Prompt(choices="Abc", hidden="Xyz")
    assert prompt.hidden == list("Xyz")
    assert prompt.valid_choices == list("abcxyz")


def test_prompt_valid_choices():
    prompt = Prompt(choices=[1, True, "YES "])
    assert prompt.valid_choices == ["1", "true", "yes"]


@pytest.mark.parametrize(["show_choices", "choices", "choices_text"], [
    ("y/n", [], r"[prompt.choices]\[y/n][/prompt.choices]"),
    (True, ["a", "b", "c"], r"[prompt.choices]\[a/b/c][/prompt.choices]"),
    (False, [], None),
])
def test_prompt_choices_text(show_choices, choices, choices_text):
    prompt = Prompt(show_choices=show_choices, choices=choices)
    assert prompt.choices_text == choices_text


@pytest.mark.parametrize(["kwargs", "tpl"], [
    ({}, "$prefix $question"),
    (
        dict(choices="abc", show_choices=True),
        r"$prefix $question [prompt.choices]\[a/b/c][/prompt.choices]"
    ),
    (
        {"show_choices": "yes/no"},
        r"$prefix $question [prompt.choices]\[yes/no][/prompt.choices]"
    ),
    (
        {"retries": 1},
        "$prefix [prompt.invalid]Try again[/prompt.invalid]"
    ),
])
def test_prompt_message(kwargs, tpl):
    prompt = Prompt("Your reply?", **kwargs)

    message = Template(tpl).substitute(
        prefix="[prompt.prefix]>[/prompt.prefix]",
        question="Your reply?"
    )

    assert prompt.message == message


def test_prompt_menu():
    expected = """
What is your favorite fruit?

  [prompt.number]1)[/prompt.number] [prompt.option]apple[/prompt.option]
  [prompt.number]2)[/prompt.number] [prompt.option]bananna[/prompt.option]
  [prompt.number]3)[/prompt.number] [prompt.option]orange[/prompt.option]
"""
    prompt = Prompt(
        preface="What is your favorite fruit?",
        choices=["apple", "bananna", "orange"],
    )

    menu = prompt.menu()

    assert menu == expected.lstrip()


def test_prompt_prompt():
    prompt = Prompt(pre_prompt=lambda: None)
    assert isinstance(prompt.prompt, RichPrompt)
    assert prompt.prompt.pre_prompt


def test_prompt_answer_ok():
    prompt = Prompt(choices="abc")
    assert prompt.answer_ok("a") is True
    assert prompt.answer_ok("A") is True
    assert prompt.answer_ok("z") is False


def test_prompt_ask_choices_map(monkeypatch, input_mock):
    with monkeypatch.context() as m:
        m.setattr("rich.prompt.PromptBase.get_input", input_mock(["2"]))
        prompt = Prompt(choices_map=dict(zip("123", "abc")))
        answer = prompt.ask()
        assert answer == "b"


@pytest.mark.parametrize(["reply", "expected"], [
    ("Y", True),
    ("y", True),
    ("yes", True),
    ("no", False),
    ("sure", False),
    ("", False),
])
def test_prompt_confirm(monkeypatch, input_mock, reply, expected):
    with monkeypatch.context() as m:
        m.setattr("rich.prompt.PromptBase.get_input", input_mock([reply]))

        prompt = Prompt("Proceed?")
        answer = prompt.confirm()

        assert answer is expected


@pytest.mark.parametrize(["responses", "expected", "lines", "kwargs"], [
    (["a"], "a", ["> Text: "], {}),
    (["z", "A"], "A", ["> Text: ", "> Try again: "], dict(choices="abc")),
])
def test_prompt_ask(
    monkeypatch,
    capsys,
    input_mock,
    responses,
    expected,
    lines,
    kwargs,
):
    with monkeypatch.context() as m:
        m.setattr("rich.prompt.PromptBase.get_input", input_mock(responses))

        prompt = Prompt("Text", **kwargs)
        answer = prompt.ask()

        output = capsys.readouterr().out.splitlines()

        assert answer == expected
        assert output == lines


def test_prompt_quit(monkeypatch, input_mock):
    """
    GIVEN: A Prompt object
    WHEN: .ask() is called and receives a response in QUIT_OPTS
    THEN: it should exit the program
    """
    with monkeypatch.context() as m:
        m.setattr("rich.prompt.PromptBase.get_input", input_mock(["q"]))

        prompt = Prompt()

        with pytest.raises(SystemExit):
            prompt.ask()


def test_prompt_max_retries(monkeypatch, capsys, input_mock):
    """
    GIVEN: A prompt object with choices
    WHEN: .ask() is called and repeatedly given invalid answers
    THEN: the prompt message should change to "Try again" after the first try
    AND: after a few more retries, a message should be printed listing the valid choices
    AND: eventually, it should abort
    """
    responses = ["x"] * 11

    try_again = "> Try again: "
    choices_message = "Please enter one of: 'a', 'b', 'c'"

    expected_output = [
        "> Text: ",
        *([try_again] * 3),
        *([choices_message, try_again] * 7),
    ]

    with monkeypatch.context() as m:
        m.setattr("rich.prompt.PromptBase.get_input", input_mock(responses))

        prompt = Prompt("Text", choices=["a", "b", "c"])

        with pytest.raises(Abort) as e:
            prompt.ask()

        output = capsys.readouterr().out.splitlines()

        assert output == expected_output
        assert str(e.value) == "Giving up."


def test_prompt_select(monkeypatch, input_mock, capsys):
    expected_output = """
Multiple versions found in /tmp/ventoy-macos-kylafimi

  1) 1.1.11
  2) 1.1.12

> Enter #1-2:
"""
    with monkeypatch.context() as m:
        m.setattr("rich.prompt.PromptBase.get_input", input_mock(["1"]))

        prompt = Prompt.select(
            choices=["1.1.11", "1.1.12"],
            preface="Multiple versions found in /tmp/ventoy-macos-kylafimi",
        )

        assert prompt.question == "Enter #1-2"
        assert prompt.prompt.pre_prompt
        assert prompt.choices == ["1.1.11", "1.1.12"]
        assert prompt.hidden == ["1", "2"]
        assert prompt.choices_map == {"1": "1.1.11", "2": "1.1.12"}

        answer = prompt.ask()

        output = capsys.readouterr().out

        assert answer == "1.1.11"
        assert output == expected_output.strip() + " \n"


def test_prompt_choices_map():
    prompt = Prompt(choices_map={"Abc": 123, " xYz ": 321, 666: "xxx"})
    assert prompt.choices_map == {"abc": 123, "xyz": 321, "666": "xxx"}

#  @pytest.mark.skip
#  def test_prompt_():
#      ...
