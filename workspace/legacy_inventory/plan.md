# Refactoring plan: legacy inventory module

## 1. Code smells

- **Module-level mutable global (`inv`) plus a useless `global inv` statement.** Hidden shared state makes tests order-dependent and prevents multiple inventories.
- **Single "god function" `do_stuff` that dispatches on a string.** The name says nothing, and the signature is shared by four unrelated operations (`qty`/`price` are meaningless for `total`/`report`; `name` is required even for them).
- **Magic string actions with silent fallthrough.** A typo such as `"ad"` is a silent no-op.
- **Positional list as a record (`inv[name][0]`, `[1]`).** Index meanings are undocumented and error-prone.
- **Mixed return types by branch.** `add`/`remove` return `None`, `total` returns a number, and `report` returns `str`, which makes the function hard to use and type.
- **Manual string concatenation and accumulation loops.** They are verbose and fragile (`k + ": "` raises `TypeError` for non-str names).
- **No validation, no docs, no type hints.** Negative or zero quantities and prices are silently accepted, and `add` on an existing item silently ignores `price`. These are surprising, undocumented behaviors.
- **Mutation-and-delete logic inline.** The "remove deletes the entry at `<= 0`" rule is buried in a branch, which hides a business rule.

## 2. Target design (`refactored.py`)

```python
from dataclasses import dataclass

@dataclass
class Item:
    qty: float      # int in practice; no coercion
    price: float

class Inventory:
    def __init__(self) -> None: ...
        # self._items: dict[str, Item]  (insertion-ordered)
    def add(self, name: str, qty: float = 0, price: float = 0) -> None: ...
        # new name -> Item(qty, price); existing -> qty += qty, price IGNORED
    def remove(self, name: str, qty: float = 0) -> None: ...
        # missing -> no-op; else qty -= qty; delete if resulting qty <= 0
    def total(self) -> float: ...
        # explicit loop: t = 0; t = t + qty*price per item in insertion order
    def report(self) -> str: ...
        # one line per item: f"{name}: {qty} @ ${price}\n" using str() semantics
    def __contains__(self, name: str) -> bool: ...
    def __len__(self) -> int: ...

_default = Inventory()   # backs the legacy shim only

def do_stuff(action, name, qty=0, price=0):
    """Backward-compatible shim. Delegates to _default."""
```

**`do_stuff` shim:**
- Keeps the identical signature (`name` stays required positionally).
- Dispatches `"add"` → `_default.add(name, qty, price)`, `"remove"` → `_default.remove(name, qty)`, `"total"` → `return _default.total()`, `"report"` → `return _default.report()`.
- Any other action returns `None` and does nothing.
- Dispatch can be an `if/elif` or a small dict of lambdas. Do not introduce an Enum that raises on unknown values.

**Implementation notes:**
- Use an explicit accumulation loop in `total`, **not** `sum()`. Python 3.12+ `sum()` uses compensated float summation and can return different results from the original.
- Keep `str(qty)` and `str(price)` formatting in `report` (e.g. `5.0` prints as `5.0`, with no rounding or `:.2f`).
- Use f-strings, but output must be byte-identical to the legacy output.

## 3. Behavior to preserve

**`add`**
- If the name is new, store `qty` and `price` exactly as given. There is no validation, so zero or negative qty and price are accepted. A new item with `qty <= 0` is stored and **not** deleted.
- If the name already exists, add `qty` to the stored quantity. The passed `price` is **ignored** and the original price is kept. The quantity is not deleted even if the result is `<= 0`.
- Returns `None`.

**`remove`**
- If the name is missing, this is a silent no-op with no error.
- Otherwise subtract `qty`. If the result is `<= 0`, delete the entry. This covers over-removal, which does not raise or clamp.
- `remove` with the default `qty=0` on an item whose stored qty is `<= 0` deletes it. On a positive-qty item it changes nothing.
- A negative `qty` increases stock.
- Returns `None`.

**`total`**
- Returns the sum of `qty * price` over all items, including negative or zero quantities.
- An empty inventory returns the int `0`.
- The numeric type follows Python arithmetic (int stays int, float propagates).
- Summation order is insertion order, with the same left-to-right float accumulation.

**`report`**
- Returns `""` for an empty inventory.
- Otherwise returns one `"{name}: {qty} @ ${price}\n"` line per item, in insertion order. Every line, including the last, ends with `\n`.
- A re-added existing item keeps its original position.
- An item deleted and re-added moves to the end.
- A non-str name raises `TypeError` in `report` only. Add, remove and total accept any hashable name. This is acceptable either to preserve or to leave undocumented, but do not add validation.

**`do_stuff` general**
- An unknown action returns `None` with no state change and no exception.
- Calling without `name` raises `TypeError` (signature preserved).
- `"total"` and `"report"` ignore `qty` and `price`; `"remove"` ignores `price`.
- State persists across calls within the process (the default shared inventory).

## 4. Improvements

Keep these minimal:

1. **The global `inv` dict is no longer exposed.** State lives in `Inventory._items` and the private `_default`. This is the point of the refactor. Any external code that touched `inv` directly must migrate to `Inventory`, and the implementer should grep for such usage.
2. **Type hints and docstrings added.** Docstrings must call out the quirks (price ignored on re-add, delete at `<= 0`) as intentional legacy semantics.

Deliberately **not** changed, but worth a follow-up ticket: input validation, an error on unknown actions, an error on removing a missing item, and updating the price on re-add.

## 5. Test plan (pytest)

Use a fresh `Inventory()` per test. For `do_stuff` tests, use a fixture that resets `refactored._default = Inventory()` (or monkeypatches it).

1. `test_add_new_item_report`: `add("apple", 3, 0.5)` → `report() == "apple: 3 @ $0.5\n"`.
2. `test_add_existing_accumulates_qty_ignores_price`: `add("a", 2, 1.0)`, `add("a", 3, 9.0)` → qty 5 and price 1.0 (`report() == "a: 5 @ $1.0\n"`).
3. `test_add_zero_or_negative_qty_new_item_is_kept`: `add("x", 0, 5)` → `"x" in inv`, and `report() == "x: 0 @ $5\n"`.
4. `test_remove_partial`: add 5, remove 2 → qty 3 remains.
5. `test_remove_exact_deletes`: add 5, remove 5 → `"a" not in inv`.
6. `test_remove_more_than_stock_deletes_no_error`: add 2, remove 10 → item gone, no exception.
7. `test_remove_missing_is_noop`: `remove("ghost", 1)` raises nothing, and `len(inv) == 0`.
8. `test_remove_default_qty_deletes_nonpositive_item_only`: an item with qty 0 is deleted by `remove("x")`, while an item with qty 4 is unchanged by `remove("y")`.
9. `test_remove_negative_qty_increases_stock`: add 5, `remove("a", -3)` → qty 8.
10. `test_total_empty_is_int_zero`: `total() == 0 and isinstance(total(), int)`.
11. `test_total_multiple_items_and_float_exactness`: e.g. `add("a", 2, 0.1)` and `add("b", 1, 0.2)` → `total() == 2 * 0.1 + 1 * 0.2` (the explicit-loop value, not `math.fsum`).
12. `test_report_empty_and_order`: empty gives `""`. After add a, add b, add a again, the order is a, b. After remove a then add a, the order is b, a.
13. `test_report_str_formatting`: price `5.0` renders `$5.0`, and an int price renders `$5`. Each line ends with `\n`.
14. `test_do_stuff_dispatch_roundtrip`: `do_stuff("add","a",2,3)` returns `None`, `do_stuff("total","")` returns `6`, `do_stuff("report","")` returns `"a: 2 @ $3\n"`, and `do_stuff("remove","a",2)` returns `None` and empties the inventory.
15. `test_do_stuff_unknown_action_and_missing_name`: `do_stuff("bogus","a")` returns `None` and leaves state unchanged, and `do_stuff("total")` raises `TypeError`.