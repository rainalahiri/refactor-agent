import refactored
from refactored import parse


def test_basic_types():
    assert parse("a=1\nb=true\nc=hello") == {"a": 1, "b": True, "c": "hello"}


def test_bool_case_insensitive():
    r = parse("a=TRUE\nb=False")
    assert r["a"] is True
    assert r["b"] is False


def test_one_and_zero_are_ints():
    r = parse("a=1\nb=0")
    assert type(r["a"]) is int
    assert type(r["b"]) is int
    assert r == {"a": 1, "b": 0}


def test_negative_plus_and_leading_zero_ints():
    r = parse("a=-3\nb=+5\nc=007")
    assert r == {"a": -3, "b": 5, "c": 7}


def test_non_int_numbers_stay_strings():
    r = parse("a=1.5\nb=0x10")
    assert r == {"a": "1.5", "b": "0x10"}


def test_whitespace_stripped():
    assert parse("  key  =  val  ") == {"key": "val"}


def test_comments_and_blank_lines_skipped():
    assert parse("# c\n\n   \n  # indented\na=1") == {"a": 1}


def test_line_without_equals_ignored():
    assert parse("junk\na=1") == {"a": 1}


def test_multiple_equals_truncates():
    assert parse("a=b=c") == {"a": "b"}
    assert parse("a==5") == {"a": ""}


def test_empty_key_and_empty_value():
    assert parse("=5") == {"": 5}
    assert parse("a=") == {"a": ""}


def test_inline_comment_not_stripped():
    assert parse("a=1 # x") == {"a": "1 # x"}


def test_crlf_line_endings():
    assert parse("a=1\r\nb=true\r\n") == {"a": 1, "b": True}


def test_duplicate_keys_last_wins_and_defaults_merge():
    assert parse("a=2\na=3", {"a": 1, "z": "d"}) == {"a": 3, "z": "d"}
    r = parse("b=1", {"k": "5"})
    assert r["k"] == "5"
    assert isinstance(r["k"], str)


def test_no_shared_state_between_calls():
    parse("a=1")
    assert parse("b=2") == {"b": 2}


def test_defaults_not_mutated():
    d = {"x": 1}
    r = parse("y=2", d)
    assert d == {"x": 1}
    assert r == {"x": 1, "y": 2}
    assert r is not d


def test_override_keeps_insertion_position():
    r = parse("a=9", {"a": 1, "b": 2})
    assert list(r.items()) == [("a", 9), ("b", 2)]


def test_empty_text_returns_defaults_copy():
    assert parse("") == {}
    d = {"a": 1}
    r = parse("", d)
    assert r == d and r is not d
    assert type(r) is dict
