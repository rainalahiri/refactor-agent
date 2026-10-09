# Refactoring Plan: legacy inventory module

## 1. Code smells

- **Global mutable state (`inv`)**: hidden shared state makes tests order-dependent and prevents multiple inventories. The `global inv` statement is also unnecessary, since the dict is never rebound.
- **God function `do_stuff`**: one function does four unrelated jobs, selected by a string flag. The name says nothing, and the return type varies (`None`, number, or `str`).
- **Magic string actions with silent fallthrough**: a typo like `"ad"` is silently ignored. This is risky, but it is current behavior.
- **Unused parameters per action**: `qty` and `price` mean nothing for `total` and `report`, and `name` means nothing for either of them but is still required.
- **Parallel-index list storage (`inv[name][0]`, `[1]`)**: magic indices are unreadable and error-prone. A named structure is clearer.
- **Repeated dict lookups and `x = x + y`**: noisy code that hides intent.
- **String concatenation in a loop and `str()` calls**: slow and verbose. Use `join` or f-strings, but the output format must stay identical.
- **No docstrings or type hints**: the semantics are undocumented, including the quirks that price is ignored on restock and that over-removal deletes the item.

## 2. Target design (`refactored.py`)

```python
from dataclasses import dataclass

@dataclass
class _Item:
    qty: float      # int/float, whatever the caller supplied
    price: float

class Inventory:
    def __init__(self) -> None: ...
        # self._items: dict[str, _Item]  (insertion-ordered)

    def add(self, name: str, qty=0, price=0) -> None:
        """New name -> store _Item(qty, price). Existing name -> qty += qty; price is NOT updated."""

    def remove(self, name: str, qty=0) -> None:
        """Missing name -> silent no-op. Else qty -= qty; if result <= 0, delete the item."""

    def total(self):
        """Sum of qty*price over all items; returns int 0 when empty."""

    def report(self) -> str:
        """One line per item in insertion order: f"{name}: {qty} @ ${price}\n"; '' when empty."""

    def quantity(self, name: str):
        """Return the qty, or None if absent (read-only helper, mainly for tests)."""

    def __contains__(self, name: str) -> bool: ...
    def __len__(self) -> int: ...

_default_inventory = Inventory()

def reset_default_inventory() -> None:
    """Replace the module-level default with a fresh Inventory (test helper)."""

def do_stuff(action, name, qty=0, price=0):
    """Backward-compatible facade. Dispatches to _default_inventory:
       'add'    -> add(name, qty, price); returns None
       'remove' -> remove(name, qty);     returns None
       'total'  -> total()
       'report' -> report()
       anything else -> no-op, returns None"""
```

Notes for the implementer:
- Implement the facade with an `if`/`elif` chain or a small dispatch dict. Keep the signature exactly `do_stuff(action, name, qty=0, price=0)`, with `name` still required.
- Do not add validation to `Inventory`.
- `_default_inventory` must be looked up at call time, not bound at definition time, so `reset_default_inventory` works.

## 3. Behavior to preserve

- **add, new name**: stores `(qty, price)` with defaults `0` and `0`. Zero or negative quantities are accepted, and an item with `qty=0` is stored and stays.
- **add, existing name**: `qty` is incremented. The `price` argument is **ignored**, so the original price is kept. Adding a negative qty may take the total to `<= 0`, and the item is **not** deleted on add.
- **remove, missing name**: silent no-op, with no exception.
- **remove, existing name**: `qty` is subtracted. If the result is `<= 0` the item is deleted. This includes over-removal (e.g. 5 minus 10), which deletes the item without error. `remove(name)` with the default `qty=0` deletes an item whose qty is already `<= 0`, and leaves a positive-qty item unchanged. A negative remove qty increases the stock.
- **total**: sum of `qty * price`. An empty inventory returns the int `0`. Negative-qty items contribute negatively. Result types follow the inputs (int stays int, float stays float).
- **report**: lines are `"{name}: {qty} @ ${price}\n"` in insertion order. A re-added item (after deletion) goes to the end. Values are formatted with plain `str()`, so `2.5` gives `$2.5` and `10` gives `$10`, with no rounding or padding. An empty inventory returns `""`. Every line, including the last, ends in `\n`.
- **Unknown action**: returns `None`, with no state change and no exception.
- **Return values**: `add` and `remove` return `None`. `total` and `report` return their values.
- **Argument handling**: `name` is a required positional argument even for `total` and `report`. Calling `do_stuff("total")` raises `TypeError`. A non-str name in `report` raises `TypeError`, because it is concatenated with `str` (an f-string would not raise, so either keep this behavior or accept it as a documented edge, and decide explicitly).
- **State across calls**: state persists across `do_stuff` calls in one process, as the module-level default inventory.

## 4. Improvements

1. **`inv` is no longer a public module global.** State lives in `Inventory` and a private default instance. The legacy dict-of-lists shape is not retained. Justification: this removes the global-state smell, and `do_stuff` keeps working for existing callers. If external code reads `inv` directly, flag this before merging.
2. **Non-str names in `report`**: the original raises `TypeError` via `k + ": "`. The refactor should keep this by using `name + ": "` or an explicit `str` check, so there is no behavior change. This is listed for the implementer's attention, and it is not an improvement.

Everything else is unchanged, including the quirks (price ignored on restock, silent unknown actions, silent over-removal).

## 5. Test plan (pytest)

Use an autouse fixture that calls `reset_default_inventory()`. Tests 1–10 and 12–13 use `Inventory` directly or `do_stuff`.

1. `test_add_new_item_and_report`: add `"apple", 5, 2` gives report `"apple: 5 @ $2\n"`.
2. `test_add_existing_increments_qty_keeps_original_price`: add `("a", 2, 10)` then `("a", 3, 99)` gives qty 5, report shows `$10`.
3. `test_add_zero_qty_item_is_kept`: add `("a", 0, 5)` gives `"a" in inv` and a report line `"a: 0 @ $5\n"`.
4. `test_add_negative_qty_on_existing_does_not_delete`: add 2, then add −5, the item remains with qty −3.
5. `test_remove_partial`: add 5, remove 2 gives qty 3.
6. `test_remove_exact_deletes`: add 5, remove 5 gives the item gone.
7. `test_remove_more_than_available_deletes_silently`: add 5, remove 10 gives the item gone with no exception.
8. `test_remove_missing_item_is_noop`: remove on an empty or other inventory raises nothing and changes nothing.
9. `test_remove_default_qty_zero`: remove with no qty keeps a positive-qty item, and deletes a qty-0 item.
10. `test_total_empty_returns_int_zero`: `total() == 0` and `isinstance(..., int)`.
11. `test_total_mixed_prices`: several items, including a float price, gives the correct sum.
12. `test_report_format_and_order`: floats print as `$2.5`, ints as `$10`, items appear in insertion order, and a deleted-then-re-added item moves to the end. Empty gives `""`.
13. `test_unknown_action_returns_none_and_no_change`: `do_stuff("bogus", "x", 1, 1)` returns `None` and leaves state unchanged.
14. `test_do_stuff_facade_matches_inventory_and_signature`: `do_stuff("add", ...)` and `do_stuff("remove", ...)` return `None`, `total` and `report` return values, and `do_stuff("total")` raises `TypeError`.
15. `test_differential_against_legacy`: paste the legacy function into the test file as `legacy_do_stuff`. Run a seeded random sequence of about 200 operations (add, remove, total, report, with ints and floats, names from a small pool) through both implementations. Assert that every return value is equal and that the final reports match. This is the safety net for all the quirks listed above.