# Refactoring plan: legacy inventory module

## 1. Code smells

- **Global mutable state (`inv`, plus a pointless `global inv`)**: tests and callers share hidden state, so isolation and reuse are impossible.
- **God function `do_stuff`**: it does four unrelated jobs behind a string switch. The name says nothing, and callers get no discoverable API.
- **Inconsistent return contract**: `add` and `remove` return `None`, `total` returns a number, `report` returns a string, and an unknown action returns `None`. Callers can't tell a no-op from a result.
- **Unused or misleading parameters**: `name` is required but ignored for `total` and `report`, and `price` is silently ignored when the item already exists.
- **Magic list `[qty, price]` accessed by index (`inv[k][0]`)**: this is unreadable and error-prone. A named structure would document the intent.
- **Silent failure paths**: removing a missing item and passing an unknown action both do nothing with no signal. That is risky, but the behavior is relied upon, so it is preserved and documented.
- **Manual accumulation and string building (`t = t + ...`, `s = s + ...`)**: this is verbose and quadratic for strings.
- **No docstrings or type hints, and no input validation**: the intended contract is unknown, and negative quantities and prices are accepted.

## 2. Target design (all in `refactored.py`)

```python
@dataclass
class Item:
    qty: float
    price: float
```

```python
class Inventory:
    def __init__(self) -> None: ...        # self._items: dict[str, Item] = {}
    def add(self, name: str, qty: float = 0, price: float = 0) -> None
    def remove(self, name: str, qty: float = 0) -> None
    def total_value(self) -> float          # sum(qty*price), starts from int 0
    def report(self) -> str
    def __contains__(self, name: str) -> bool   # convenience, for tests
    def quantity(self, name: str) -> float | None  # convenience; None if absent
```

Responsibilities:
- `add`: if the name exists, add `qty` to the existing quantity and leave the price untouched. Otherwise create `Item(qty, price)`.
- `remove`: if the name is missing, do nothing. Otherwise subtract `qty`, and delete the item if the resulting quantity is `<= 0`.
- `total_value`: `sum((i.qty * i.price for i in items.values()), 0)`, iterated in insertion order.
- `report`: one line per item, `f"{name}: {str(qty)} @ ${str(price)}\n"`, in insertion order, concatenated with `"".join`.

Backward-compatible shim:

```python
_default = Inventory()   # module-level; do_stuff must look it up at call time

def do_stuff(action: str, name: str, qty=0, price=0):
    # Dispatch:
    #   "add"    -> _default.add(name, qty, price); return None
    #   "remove" -> _default.remove(name, qty); return None
    #   "total"  -> return _default.total_value()
    #   "report" -> return _default.report()
    #   other    -> return None (no-op)
```

Use a small dispatch dict or an if/elif chain inside `do_stuff`. It is the only place that knows about action strings.

## 3. Behavior to preserve

- **Signature**: `do_stuff(action, name, qty=0, price=0)`. `name` stays a required positional argument even for `total` and `report`, where it is ignored.
- **`add`, new name**: creates the item with the given qty and price. This includes `qty=0`, which creates a zero-quantity entry that is *not* auto-deleted. Negative qty and price are accepted. Returns `None`.
- **`add`, existing name**: qty is increased by `qty` (negative values allowed). **The `price` argument is ignored**, so the original price is kept. The item is **not** deleted even if the new quantity is `<= 0`. Returns `None`.
- **`remove`, missing name**: silent no-op, with no exception. Returns `None`.
- **`remove`, existing name**: qty is decreased. If the result is `<= 0`, the item is deleted, so removing more than is available also deletes with no error. Default `qty=0` subtracts nothing, but it still deletes an item whose quantity is already `<= 0`, for example a zero-quantity item created by `add`.
- **`total`**: returns the sum of `qty * price` over all items. An empty inventory returns the int `0`. Numeric types are not coerced, so int stays int and float stays float.
- **`report`**: one line per item, `"<name>: <qty> @ $<price>\n"`, using plain `str()` of the numbers with no formatting, rounding or padding. An empty inventory returns `""`. Order is insertion order. An item deleted and re-added moves to the end.
- **Unknown or other action** (including `None`, or different casing like `"ADD"`): silent no-op that returns `None`.
- **State persists across `do_stuff` calls** within a process, because the default instance is shared.

## 4. Improvements (intentional changes, minimal)

1. **The global `inv` dict is no longer exposed.** State now lives in `Inventory` instances, and `do_stuff` uses a private default instance. This removes the global-state smell. The caveat is that any external code that touched `inv` directly will break, so this is a deliberate, documented break.
2. **New additive public API** (`Inventory`, `Item`) with type hints and docstrings. Nothing in the old behavior changes.

Explicitly out of scope, even though tempting:
- Raising on unknown actions.
- Validating negative quantities.
- Updating the price on a re-add.
- Formatting prices.

Each of these would change behavior and needs a separate decision.

## 5. Test plan (pytest, 14 tests)

Fixture: `monkeypatch.setattr(refactored, "_default", refactored.Inventory())` for the `do_stuff` tests. Shim tests need this fresh state, so `do_stuff` must resolve `_default` at call time.

1. `test_add_new_item`: `add("a", 5, 2.5)` gives qty 5, and the report shows `"a: 5 @ $2.5\n"`.
2. `test_add_existing_accumulates_and_keeps_original_price`: add `("a", 5, 2)`, then `("a", 3, 99)`, giving qty 8 and price 2.
3. `test_add_zero_qty_creates_entry`: `add("a", 0, 5)` leaves `"a"` present with qty 0.
4. `test_add_negative_on_existing_does_not_delete`: after `add("a", 2)` and `add("a", -5)`, `"a"` still exists with qty -3.
5. `test_remove_partial`: `add("a", 5)` then `remove("a", 2)` leaves qty 3.
6. `test_remove_exact_and_excess_delete`: removing exactly the quantity deletes the item, and so does removing more than the quantity.
7. `test_remove_missing_is_noop`: `remove("nope", 1)` raises nothing and returns `None`, and the inventory is unchanged.
8. `test_remove_default_qty_zero_quirk`: `remove("a")` on qty 5 keeps the item, but on a zero-quantity item it deletes it.
9. `test_total_empty_returns_int_zero`: `total_value() == 0` and `isinstance(..., int)`.
10. `test_total_multiple_items`: for example `(2, 1.5)` and `(3, 4)` gives `15.0`, checked with `pytest.approx` where floats are involved.
11. `test_report_format_empty_and_order`: an empty inventory gives `""`. Otherwise lines follow insertion order and end with `"\n"`.
12. `test_report_readd_moves_to_end`: add `a` and `b`, remove `a`, re-add `a`, and the order is `b` then `a`.
13. `test_do_stuff_unknown_action_noop`: `do_stuff("bogus", "a")` returns `None` and leaves state unchanged. `"ADD"` is also a no-op.
14. `test_do_stuff_shim_end_to_end_and_instance_isolation`: `do_stuff` add and remove return `None`. `total` and `report` return the expected values, and `name` is ignored (for example `do_stuff("total", "")`). Two separate `Inventory()` instances do not share state.