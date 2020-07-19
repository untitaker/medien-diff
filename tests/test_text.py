import pytest

from medien_diff.text import is_significant_title_change


@pytest.mark.parametrize("a,b", [("bar", "foo "), ("bar ", "foo "), ("", "foo "),])
def test_significant(a, b):
    assert is_significant_title_change(a, b)


@pytest.mark.parametrize(
    "a,b",
    [
        ("foo  bar", "foo bar"),
        ("live: foo  bar", "foo bar"),
        ("foo", "live: bar"),
        ("foo", "live: bar"),
        ("foo.", "foo"),
        ("Foo: 42 new things", "Foo: 43 new things"),
        ("foo", "Foo"),
        ("fo", "foo"),
        ("fooo", "foo"),
        ("blob", "blbo"),
        ("Foo under pressure from all sides", "Foo from all sides under pressure"),
        ("wurde geholt", "wurden geholt"),
    ],
)
def test_insignificant(a, b):
    assert not is_significant_title_change(a, b)
