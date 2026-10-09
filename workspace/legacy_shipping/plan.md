# Refactoring Plan: Shipping Cost Calculator

## 1. Code smells

- **Cryptic names (`ship`, `w`, `dist`, `c`, `intl`)**: the reader can't tell units or meaning, which makes mistakes easy.
- **Magic numbers (15, 2.5, 0.05, 5, 1.2, 0.02, 10, 0.15, 0.1, 50, 30, 20)**: pricing rules are buried in logic, so changing a rate means hunting through code.
- **Rates duplicated across two branches**: the domestic and international formulas have the same shape (base + per-kg + per-distance) but are written twice.
- **Mutated single variable `c` across 4 stages**: pipeline steps can't be named, tested or reordered safely. Order matters here (see section 3).
- **Inconsistent express handling**: international multiplies by 2 and domestic adds 10, with no named concept for either.
- **Awkward discount arithmetic (`c - c * 0.15`)**: it is verbose and hides the intent "tiered discount".
- **Nested ifs, no docstring, no type hints**: the order of operations and the intended input types are undocumented.
- **Boolean flag positional args (`express, intl, member`)**: call sites like `ship(5, 10, True, False, True)` are unreadable and easy to transpose.

## 2. Target design (`refactored.py`)

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class RateCard:
    base: float
    per_kg: float
    per_distance: float
    express_multiplier: float   # applied first
    express_surcharge: float    # added after multiplier

DOMESTIC = RateCard(base=5, per_kg=1.2, per_distance=0.02,
                    express_multiplier=1, express_surcharge=10)
INTERNATIONAL = RateCard(base=15, per_kg=2.5, per_distance=0.05,
                         express_multiplier=2, express_surcharge=0)

MEMBER_DISCOUNT_THRESHOLD = 50
MEMBER_DISCOUNT_HIGH = 0.15   # cost > threshold
MEMBER_DISCOUNT_LOW = 0.10    # cost <= threshold
HEAVY_WEIGHT_THRESHOLD = 30
HEAVY_SURCHARGE = 20
```

Functions (all pure, module-level, private helpers prefixed `_`):

- `_base_cost(card: RateCard, weight: float, distance: float) -> float`: returns `card.base + weight * card.per_kg + distance * card.per_distance`. **Keep this exact evaluation order** so float results are bit-identical.
- `_apply_express(card: RateCard, cost: float) -> float`: returns `cost * card.express_multiplier + card.express_surcharge`. `x*1 + 10` and `x*2 + 0` are bit-identical to the legacy `x + 10` and `x * 2`.
- `_apply_member_discount(cost: float) -> float`: picks the rate (`> threshold` is strict, so 15%, else 10%) and returns `cost - cost * rate`. **Keep this form, not `cost * 0.85`**, to avoid last-bit float differences.
- `_apply_heavy_surcharge(cost: float, weight: float) -> float`: returns `cost + HEAVY_SURCHARGE` if `weight > HEAVY_WEIGHT_THRESHOLD`, else `cost`.
- `calculate_shipping_cost(weight: float, distance: float, *, express: bool, international: bool, member: bool) -> float`: the pipeline, in this order: select card, base cost, express (if set), member discount (if set), heavy surcharge, `round(cost, 2)`. Flags are keyword-only and use truthiness, with no `is True` checks.
- `ship(w, dist, express, intl, member) -> float`: a **backward-compatible wrapper** with the identical positional signature and order. It delegates to `calculate_shipping_cost(w, dist, express=express, international=intl, member=member)`. All five arguments stay required (no defaults).

## 3. Behavior to preserve

- **Signature**: `ship(w, dist, express, intl, member)`, with positional order `express` before `intl`. All arguments are required.
- **Domestic formula**: `5 + w*1.2 + dist*0.02`; express adds a flat 10.
- **International formula**: `15 + w*2.5 + dist*0.05`; express **doubles** the whole cost, including the base.
- **Order of operations**: base, then express, then member discount, then heavy surcharge, then round.
- **Tier test**: the discount tier is decided on the cost *after express* and *before* the heavy surcharge. `cost > 50` gets 15%; `cost == 50` and below gets 10%.
- **Heavy surcharge**: a flat +20 when `w > 30` (strict, so `w == 30` gets none). It is added *after* the discount and is never discounted. It does not influence the tier choice.
- **Rounding**: `round(c, 2)` on a float, with Python's built-in semantics. The result is always a `float`.
- **Truthiness**: `express`, `intl` and `member` are tested by truthiness (`1`, `None`, `""` all work).
- **No validation**: zero, negative or huge weight and distance are computed without error or clamping (e.g. `ship(-1, 0, F, F, F) == 3.8`). Non-numeric weight or distance raises whatever `TypeError` the arithmetic raises naturally.
- **Pure function**: no state, no I/O.

## 4. Improvements

None to behavior. Added type hints, docstrings, named constants and the new keyword-only `calculate_shipping_cost` are non-behavioral. Input validation is deliberately **out of scope**, because adding it would change behavior. It can be proposed as a follow-up.

## 5. Test plan (pytest, `test_refactored.py`)

Expected values are hand-derived. Compare with `==` since outputs are rounded to 2 decimals.

1. **Domestic base**: `ship(10, 100, False, False, False) == 19.0`
2. **Domestic express (flat +10)**: `ship(10, 100, True, False, False) == 29.0`
3. **International base**: `ship(10, 1000, False, True, False) == 90.0`
4. **International express (doubling)**: `ship(10, 1000, True, True, False) == 180.0`
5. **Arg order matters**: `ship(10,100,True,False,False) == 29.0` and `ship(10,100,False,True,False) == 45.0`
6. **Member low tier (10%)**: `ship(10, 100, False, False, True) == 17.1`
7. **Member high tier (15%)**: `ship(10, 1000, False, True, True) == 76.5`
8. **Tier boundary at exactly 50**: `ship(14, 0, False, True, True) == 45.0` (10% tier). Just above: `ship(14, 1, False, True, True) == 42.54` (15% tier).
9. **Express pushes cost into the high tier**: `ship(30, 0, True, False, True) == 43.35`. Base 41, +10 = 51, 15% off. Also `ship(30, 0, False, False, True) == 36.9`.
10. **Heavy threshold is strict**: `ship(30, 0, False, False, False) == 41.0` (no surcharge) and `ship(31, 0, False, False, False) == 62.2` (+20).
11. **Surcharge is not discounted and does not affect the tier**: `ship(40, 0, False, True, True) == 117.75` and `ship(31, 0, False, False, True) == 57.98` (10% tier, then +20).
12. **Zero and negative inputs, no validation**: `ship(0,0,F,F,F) == 5.0`, `ship(0,0,F,T,F) == 15.0`, `ship(-1,0,F,F,F) == 3.8`.
13. **Truthy flags and return type**: `ship(10,100,1,0,None) == ship(10,100,True,False,False)`. Also `isinstance(ship(1,1,F,F,F), float)` and the value equals `6.22`.
14. **Characterization test against the legacy implementation**: paste the original function into the test file as `_legacy_ship`. Parametrize over a grid of `w in {0, 1, 10, 14, 29.99, 30, 30.01, 31, 100}`, `dist in {0, 1, 100, 1000, 5000}` and all 8 flag combinations. Assert `ship(...) == _legacy_ship(...)` exactly.
15. **Wrapper equivalence**: `calculate_shipping_cost(10, 100, express=True, international=False, member=True) == ship(10, 100, True, False, True)`.