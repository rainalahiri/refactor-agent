import itertools

import pytest

import refactored
from refactored import ship, calculate_shipping_cost

F = False
T = True


def _legacy_ship(w, dist, express, intl, member):
    if intl:
        c = 15 + w * 2.5 + dist * 0.05
        if express:
            c = c * 2
    else:
        c = 5 + w * 1.2 + dist * 0.02
        if express:
            c = c + 10
    if member:
        if c > 50:
            c = c - c * 0.15
        else:
            c = c - c * 0.1
    if w > 30:
        c = c + 20
    return round(c, 2)


def test_domestic_base():
    assert ship(10, 100, F, F, F) == 19.0


def test_domestic_express():
    assert ship(10, 100, T, F, F) == 29.0


def test_international_base():
    assert ship(10, 1000, F, T, F) == 90.0


def test_international_express():
    assert ship(10, 1000, T, T, F) == 180.0


def test_arg_order():
    assert ship(10, 100, True, False, False) == 29.0
    assert ship(10, 100, False, True, False) == 45.0


def test_member_low_tier():
    assert ship(10, 100, F, F, T) == 17.1


def test_member_high_tier():
    assert ship(10, 1000, F, T, T) == 76.5


def test_tier_boundary():
    assert ship(14, 0, F, T, T) == 45.0
    assert ship(14, 1, F, T, T) == 42.54


def test_express_pushes_into_high_tier():
    assert ship(30, 0, T, F, T) == 43.35
    assert ship(30, 0, F, F, T) == 36.9


def test_heavy_threshold_strict():
    assert ship(30, 0, F, F, F) == 41.0
    assert ship(31, 0, F, F, F) == 62.2


def test_surcharge_not_discounted_nor_tiered():
    assert ship(40, 0, F, T, T) == 117.75
    assert ship(31, 0, F, F, T) == 57.98


def test_zero_and_negative():
    assert ship(0, 0, F, F, F) == 5.0
    assert ship(0, 0, F, T, F) == 15.0
    assert ship(-1, 0, F, F, F) == 3.8


def test_truthy_flags_and_return_type():
    assert ship(10, 100, 1, 0, None) == ship(10, 100, True, False, False)
    result = ship(1, 1, F, F, F)
    assert isinstance(result, float)
    assert result == 6.22


def test_non_numeric_raises_type_error():
    with pytest.raises(TypeError):
        ship("a", 1, F, F, F)


@pytest.mark.parametrize(
    "w,dist,express,intl,member",
    [
        (w, d, e, i, m)
        for w in (0, 1, 10, 14, 29.99, 30, 30.01, 31, 100)
        for d in (0, 1, 100, 1000, 5000)
        for e, i, m in itertools.product((False, True), repeat=3)
    ],
)
def test_matches_legacy(w, dist, express, intl, member):
    assert ship(w, dist, express, intl, member) == _legacy_ship(
        w, dist, express, intl, member)


def test_wrapper_equivalence():
    assert calculate_shipping_cost(
        10, 100, express=True, international=False, member=True
    ) == ship(10, 100, True, False, True)


def test_keyword_only_flags():
    with pytest.raises(TypeError):
        calculate_shipping_cost(10, 100, True, False, True)


def test_ship_requires_all_args():
    with pytest.raises(TypeError):
        ship(10, 100, True, False)


def test_rate_cards_frozen():
    with pytest.raises(Exception):
        refactored.DOMESTIC.base = 1
