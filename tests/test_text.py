from medien_diff.text import is_significant_title_change


def test_is_significant_title_change():
    assert is_significant_title_change("bar", "foo ")
    assert is_significant_title_change("bar ", "foo ")
    assert is_significant_title_change("", "foo ")
    assert not is_significant_title_change("foo  bar", "foo bar")
    assert not is_significant_title_change("live: foo  bar", "foo bar")
    assert not is_significant_title_change("foo", "live: bar")
    assert not is_significant_title_change("foo", "live: bar")
    assert not is_significant_title_change("foo.", "foo")
