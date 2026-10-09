import pytest

import refactored
from refactored import Inventory, do_stuff


@pytest.fixture
def inv():
    return Inventory()


@pytest.fixture
def shim(monkeypatch):
    monkeypatch.setattr(refactored, "_default", Inventory())
    return refactored


def test_add_new_item_report(inv):
    inv.add("apple", 3, 0.5)
    assert inv.report() == "apple: 3 @ $0.5\n"


def test_add_existing_accumulates_qty_ignores_price(inv):
    inv.add("a", 2, 1.0)
    inv.add("a", 3, 9.0)
    assert inv.report() == "a: 5 @ $1.0\n"


def test_add_zero_or_negative_qty_new_item_is_kept(inv):
    inv.add("x", 0, 5)
    assert "x" in inv
    assert inv.report() == "x: 0 @ $5\n"
    inv.add("y", -2, 1)
    assert "y" in inv
    assert "y: -2 @ $1\n" in inv.report()


def test_remove_partial(inv):
    inv.add("a", 5, 1)
    inv.remove("a", 2)
    assert inv.report() == "a: 3 @ $1\n"


def test_remove_exact_deletes(inv):
    inv.add("a", 5, 1)
    inv.remove("a", 5)
    assert "a" not in inv


def test_remove_more_than_stock_deletes_no_error(inv):
    inv.add("a", 2, 1)
    inv.remove("a", 10)
    assert "a" not in inv
    assert len(inv) == 0


def test_remove_missing_is_noop(inv):
    inv.remove("ghost", 1)
    assert len(inv) == 0


def test_remove_default_qty_deletes_nonpositive_item_only(inv):
    inv.add("x", 0, 5)
    inv.add("y", 4, 1)
    inv.remove("x")
    inv.remove("y")
    assert "x" not in inv
    assert "y" in inv
    assert inv.report() == "y: 4 @ $1\n"


def test_remove_negative_qty_increases_stock(inv):
    inv.add("a", 5, 1)
    inv.remove("a", -3)
    assert inv.report() == "a: 8 @ $1\n"


def test_total_empty_is_int_zero(inv):
    assert inv.total() == 0
    assert isinstance(inv.total(), int)


def test_total_multiple_items_and_float_exactness(inv):
    inv.add("a", 2, 0.1)
    inv.add("b", 1, 0.2)
    assert inv.total() == 2 * 0.1 + 1 * 0.2


def test_total_includes_negative_quantities(inv):
    inv.add("a", -2, 3)
    inv.add("b", 1, 4)
    assert inv.total() == -2


def test_report_empty_and_order(inv):
    assert inv.report() == ""
    inv.add("a", 1, 1)
    inv.add("b", 1, 1)
    inv.add("a", 1, 1)
    assert inv.report() == "a: 2 @ $1\nb: 1 @ $1\n"
    inv.remove("a", 2)
    inv.add("a", 1, 1)
    assert inv.report() == "b: 1 @ $1\na: 1 @ $1\n"


def test_report_str_formatting(inv):
    inv.add("f", 1, 5.0)
    inv.add("i", 2, 5)
    out = inv.report()
    assert out == "f: 1 @ $5.0\ni: 2 @ $5\n"
    assert out.endswith("\n")
    assert all(line for line in out.split("\n")[:-1])


def test_do_stuff_dispatch_roundtrip(shim):
    assert do_stuff("add", "a", 2, 3) is None
    assert do_stuff("total", "") == 6
    assert do_stuff("report", "") == "a: 2 @ $3\n"
    assert do_stuff("remove", "a", 2) is None
    assert len(refactored._default) == 0


def test_do_stuff_state_persists(shim):
    do_stuff("add", "a", 1, 1)
    do_stuff("add", "a", 1, 5)
    assert do_stuff("report", "") == "a: 2 @ $1\n"


def test_do_stuff_unknown_action_and_missing_name(shim):
    do_stuff("add", "a", 1, 1)
    assert do_stuff("bogus", "a") is None
    assert do_stuff("report", "") == "a: 1 @ $1\n"
    with pytest.raises(TypeError):
        do_stuff("total")
