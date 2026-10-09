import random

import pytest

import refactored
from refactored import Inventory, do_stuff, reset_default_inventory


@pytest.fixture(autouse=True)
def _reset():
    reset_default_inventory()
    yield
    reset_default_inventory()


# ---- legacy implementation (pasted) ----
inv = {}


def legacy_do_stuff(action, name, qty=0, price=0):
    global inv
    if action == "add":
        if name in inv:
            inv[name][0] = inv[name][0] + qty
        else:
            inv[name] = [qty, price]
    elif action == "remove":
        if name in inv:
            inv[name][0] = inv[name][0] - qty
            if inv[name][0] <= 0:
                del inv[name]
    elif action == "total":
        t = 0
        for k in inv:
            t = t + inv[k][0] * inv[k][1]
        return t
    elif action == "report":
        s = ""
        for k in inv:
            s = s + k + ": " + str(inv[k][0]) + " @ $" + str(inv[k][1]) + "\n"
        return s


def test_add_new_item_and_report():
    i = Inventory()
    i.add("apple", 5, 2)
    assert i.report() == "apple: 5 @ $2\n"


def test_add_existing_increments_qty_keeps_original_price():
    i = Inventory()
    i.add("a", 2, 10)
    i.add("a", 3, 99)
    assert i.quantity("a") == 5
    assert i.report() == "a: 5 @ $10\n"


def test_add_zero_qty_item_is_kept():
    i = Inventory()
    i.add("a", 0, 5)
    assert "a" in i
    assert i.report() == "a: 0 @ $5\n"


def test_add_negative_qty_on_existing_does_not_delete():
    i = Inventory()
    i.add("a", 2, 1)
    i.add("a", -5, 1)
    assert "a" in i
    assert i.quantity("a") == -3


def test_remove_partial():
    i = Inventory()
    i.add("a", 5, 1)
    i.remove("a", 2)
    assert i.quantity("a") == 3


def test_remove_exact_deletes():
    i = Inventory()
    i.add("a", 5, 1)
    i.remove("a", 5)
    assert "a" not in i
    assert len(i) == 0


def test_remove_more_than_available_deletes_silently():
    i = Inventory()
    i.add("a", 5, 1)
    i.remove("a", 10)
    assert "a" not in i


def test_remove_missing_item_is_noop():
    i = Inventory()
    i.remove("ghost", 3)
    assert len(i) == 0
    i.add("a", 4, 1)
    i.remove("ghost", 3)
    assert len(i) == 1
    assert i.quantity("a") == 4


def test_remove_default_qty_zero():
    i = Inventory()
    i.add("pos", 3, 1)
    i.add("zero", 0, 1)
    i.remove("pos")
    i.remove("zero")
    assert i.quantity("pos") == 3
    assert "zero" not in i


def test_remove_negative_qty_increases_stock():
    i = Inventory()
    i.add("a", 3, 1)
    i.remove("a", -2)
    assert i.quantity("a") == 5


def test_quantity_missing_is_none():
    assert Inventory().quantity("nope") is None


def test_total_empty_returns_int_zero():
    t = Inventory().total()
    assert t == 0
    assert isinstance(t, int)


def test_total_mixed_prices():
    i = Inventory()
    i.add("a", 2, 3)
    i.add("b", 4, 2.5)
    i.add("c", -1, 4)
    assert i.total() == 2 * 3 + 4 * 2.5 - 4
    assert i.total() == 12.0


def test_total_int_stays_int():
    i = Inventory()
    i.add("a", 2, 3)
    assert isinstance(i.total(), int)


def test_report_format_and_order():
    i = Inventory()
    assert i.report() == ""
    i.add("a", 1, 2.5)
    i.add("b", 2, 10)
    i.add("c", 3, 1)
    assert i.report() == "a: 1 @ $2.5\nb: 2 @ $10\nc: 3 @ $1\n"
    i.remove("a", 1)
    i.add("a", 7, 4)
    assert i.report() == "b: 2 @ $10\nc: 3 @ $1\na: 7 @ $4\n"


def test_report_non_str_name_raises_type_error():
    i = Inventory()
    i.add(1, 1, 1)
    with pytest.raises(TypeError):
        i.report()


def test_unknown_action_returns_none_and_no_change():
    do_stuff("add", "a", 1, 1)
    before = do_stuff("report", "x")
    assert do_stuff("bogus", "x", 1, 1) is None
    assert do_stuff("report", "x") == before
    assert do_stuff("ad", "z", 1, 1) is None
    assert do_stuff("report", "x") == before


def test_do_stuff_facade_matches_inventory_and_signature():
    assert do_stuff("add", "a", 2, 3) is None
    assert do_stuff("total", "x") == 6
    assert do_stuff("report", "x") == "a: 2 @ $3\n"
    assert do_stuff("remove", "a", 2) is None
    assert do_stuff("total", "x") == 0
    assert do_stuff("report", "x") == ""
    with pytest.raises(TypeError):
        do_stuff("total")


def test_default_inventory_persists_and_resets():
    do_stuff("add", "a", 1, 1)
    assert do_stuff("report", "x") == "a: 1 @ $1\n"
    reset_default_inventory()
    assert do_stuff("report", "x") == ""


def test_differential_against_legacy():
    inv.clear()
    reset_default_inventory()
    rng = random.Random(12345)
    names = ["a", "b", "c", "d", "e"]
    nums = [0, 1, 2, 3, 5, 10, 2.5, 0.5, -1, -3]
    actions = ["add", "remove", "total", "report"]
    for _ in range(200):
        action = rng.choice(actions)
        name = rng.choice(names)
        qty = rng.choice(nums)
        price = rng.choice(nums)
        expected = legacy_do_stuff(action, name, qty, price)
        actual = do_stuff(action, name, qty, price)
        assert actual == expected
        assert type(actual) is type(expected)
    assert do_stuff("report", "x") == legacy_do_stuff("report", "x")
    assert do_stuff("total", "x") == legacy_do_stuff("total", "x")
    inv.clear()
