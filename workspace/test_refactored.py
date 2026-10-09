import pytest

import refactored
from refactored import Inventory, do_stuff


@pytest.fixture
def inv():
    return Inventory()


@pytest.fixture
def shim(monkeypatch):
    fresh = Inventory()
    monkeypatch.setattr(refactored, "_default_inventory", fresh)
    return fresh


def test_add_new_item(inv):
    inv.add_item("apple", 5, 2)
    assert inv.report() == "apple: 5 @ $2\n"


def test_add_existing_accumulates(inv):
    inv.add_item("apple", 5, 2)
    inv.add_item("apple", 3, 2)
    assert inv.report() == "apple: 8 @ $2\n"


def test_add_existing_ignores_new_price(inv):
    inv.add_item("a", 1, 2)
    inv.add_item("a", 1, 99)
    assert inv.report() == "a: 2 @ $2\n"


def test_add_defaults(inv):
    inv.add_item("x")
    assert inv.report() == "x: 0 @ $0\n"


def test_remove_partial(inv):
    inv.add_item("a", 5, 1)
    inv.remove_item("a", 2)
    assert inv.report() == "a: 3 @ $1\n"


def test_remove_to_zero_deletes(inv):
    inv.add_item("a", 5, 1)
    inv.remove_item("a", 5)
    assert inv.report() == ""


def test_over_remove_deletes(inv):
    inv.add_item("a", 3, 1)
    inv.remove_item("a", 10)
    assert inv.report() == ""


def test_remove_missing_noop(inv, shim):
    inv.add_item("a", 1, 1)
    assert inv.remove_item("ghost", 1) is None
    assert inv.report() == "a: 1 @ $1\n"
    assert do_stuff("remove", "ghost", 1) is None
    assert do_stuff("report", "") == ""


def test_remove_qty_zero(inv):
    inv.add_item("a", 2, 1)
    inv.remove_item("a")
    assert inv.report() == "a: 2 @ $1\n"
    inv.add_item("z", 0, 1)
    inv.remove_item("z")
    assert inv.report() == "a: 2 @ $1\n"


def test_negative_add_keeps_item_and_total(inv):
    inv.add_item("a", 2, 3)
    inv.add_item("a", -5, 0)
    assert inv.report() == "a: -3 @ $3\n"
    assert inv.total_value() == -9


def test_total(inv):
    assert inv.total_value() == 0
    inv.add_item("a", 2, 3)
    inv.add_item("b", 4, 0.5)
    assert inv.total_value() == pytest.approx(8.0)


def test_report_format_and_order(inv):
    assert inv.report() == ""
    inv.add_item("a", 1, 2.5)
    inv.add_item("b", 2, 1)
    assert inv.report() == "a: 1 @ $2.5\nb: 2 @ $1\n"
    inv.remove_item("a", 1)
    inv.add_item("a", 3, 4)
    assert inv.report() == "b: 2 @ $1\na: 3 @ $4\n"


def test_shim_round_trip(shim):
    assert do_stuff("add", "a", 2, 1.5) is None
    assert do_stuff("total", "") == 3.0
    assert do_stuff("report", "") == "a: 2 @ $1.5\n"
    assert do_stuff("remove", "a", 2) is None
    assert do_stuff("report", "") == ""
    assert do_stuff("total", "") == 0


def test_shim_edge_cases(shim):
    assert do_stuff("bogus", "a", 1, 1) is None
    assert do_stuff("ADD", "a", 1, 1) is None
    assert do_stuff("report", "") == ""
    with pytest.raises(TypeError):
        do_stuff("total")
    first, second = Inventory(), Inventory()
    first.add_item("a", 1, 1)
    assert second.report() == ""
