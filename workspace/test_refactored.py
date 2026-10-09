import pytest

import refactored
from refactored import Inventory, do_stuff


@pytest.fixture
def fresh(monkeypatch):
    inv = Inventory()
    monkeypatch.setattr(refactored, "_default", inv)
    return inv


def test_add_new_item():
    inv = Inventory()
    inv.add("a", 5, 2.5)
    assert inv.quantity("a") == 5
    assert inv.report() == "a: 5 @ $2.5\n"


def test_add_existing_accumulates_and_keeps_original_price():
    inv = Inventory()
    inv.add("a", 5, 2)
    inv.add("a", 3, 99)
    assert inv.quantity("a") == 8
    assert inv._items["a"].price == 2


def test_add_zero_qty_creates_entry():
    inv = Inventory()
    inv.add("a", 0, 5)
    assert "a" in inv
    assert inv.quantity("a") == 0


def test_add_negative_on_existing_does_not_delete():
    inv = Inventory()
    inv.add("a", 2)
    inv.add("a", -5)
    assert "a" in inv
    assert inv.quantity("a") == -3


def test_remove_partial():
    inv = Inventory()
    inv.add("a", 5)
    inv.remove("a", 2)
    assert inv.quantity("a") == 3


def test_remove_exact_and_excess_delete():
    inv = Inventory()
    inv.add("a", 5)
    inv.remove("a", 5)
    assert "a" not in inv
    inv.add("b", 5)
    inv.remove("b", 10)
    assert "b" not in inv


def test_remove_missing_is_noop():
    inv = Inventory()
    inv.add("a", 1, 1)
    before = inv.report()
    assert inv.remove("nope", 1) is None
    assert inv.report() == before
    assert "nope" not in inv


def test_remove_default_qty_zero_quirk():
    inv = Inventory()
    inv.add("a", 5)
    inv.remove("a")
    assert "a" in inv
    inv.add("z", 0)
    inv.remove("z")
    assert "z" not in inv


def test_total_empty_returns_int_zero():
    total = Inventory().total_value()
    assert total == 0
    assert isinstance(total, int)


def test_total_multiple_items():
    inv = Inventory()
    inv.add("a", 2, 1.5)
    inv.add("b", 3, 4)
    assert inv.total_value() == pytest.approx(15.0)
    ints = Inventory()
    ints.add("a", 2, 3)
    assert isinstance(ints.total_value(), int)
    assert ints.total_value() == 6


def test_report_format_empty_and_order():
    inv = Inventory()
    assert inv.report() == ""
    inv.add("b", 1, 2)
    inv.add("a", 3, 4.5)
    assert inv.report() == "b: 1 @ $2\na: 3 @ $4.5\n"


def test_report_readd_moves_to_end():
    inv = Inventory()
    inv.add("a", 1, 1)
    inv.add("b", 2, 2)
    inv.remove("a", 1)
    inv.add("a", 1, 1)
    assert inv.report() == "b: 2 @ $2\na: 1 @ $1\n"


def test_do_stuff_unknown_action_noop(fresh):
    do_stuff("add", "x", 1, 1)
    before = fresh.report()
    assert do_stuff("bogus", "a") is None
    assert do_stuff("ADD", "a", 5, 5) is None
    assert do_stuff(None, "a") is None
    assert fresh.report() == before
    assert "a" not in fresh


def test_do_stuff_shim_end_to_end_and_instance_isolation(fresh):
    assert do_stuff("add", "a", 4, 2.5) is None
    assert do_stuff("add", "b", 1, 1) is None
    assert do_stuff("remove", "b", 1) is None
    assert do_stuff("total", "") == pytest.approx(10.0)
    assert do_stuff("report", "ignored") == "a: 4 @ $2.5\n"
    assert fresh.quantity("a") == 4
    other = Inventory()
    other.add("q", 1, 1)
    assert "q" not in fresh
    assert "a" not in other
