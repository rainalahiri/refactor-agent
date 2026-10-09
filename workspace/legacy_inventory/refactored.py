from dataclasses import dataclass


@dataclass
class Item:
    """A stock record: quantity and unit price (no coercion or validation)."""
    qty: float
    price: float


class Inventory:
    """An insertion-ordered inventory preserving legacy semantics."""

    def __init__(self) -> None:
        self._items: dict = {}

    def add(self, name, qty=0, price=0) -> None:
        """Add stock.

        New name: stored exactly as given (no validation; qty <= 0 is kept).
        Existing name: qty is added; the passed price is IGNORED (intentional
        legacy semantics) and the original price is kept. The item is not
        deleted even if the resulting qty is <= 0.
        """
        item = self._items.get(name)
        if item is not None:
            item.qty = item.qty + qty
        else:
            self._items[name] = Item(qty, price)

    def remove(self, name, qty=0) -> None:
        """Remove stock.

        Missing name: silent no-op. Otherwise subtract qty; if the resulting
        qty is <= 0 the entry is deleted (intentional legacy semantics; no
        error or clamping on over-removal). A negative qty increases stock.
        """
        item = self._items.get(name)
        if item is None:
            return
        item.qty = item.qty - qty
        if item.qty <= 0:
            del self._items[name]

    def total(self):
        """Return the sum of qty * price in insertion order.

        Uses an explicit left-to-right accumulation (not sum()) to keep
        float results identical to the legacy code. Empty -> int 0.
        """
        t = 0
        for item in self._items.values():
            t = t + item.qty * item.price
        return t

    def report(self) -> str:
        """Return one '<name>: <qty> @ $<price>\\n' line per item."""
        s = ""
        for name, item in self._items.items():
            s = s + f"{name}: {item.qty!s} @ ${item.price!s}\n"
        return s

    def __contains__(self, name) -> bool:
        return name in self._items

    def __len__(self) -> int:
        return len(self._items)


_default = Inventory()  # backs the legacy shim only


def do_stuff(action, name, qty=0, price=0):
    """Backward-compatible shim delegating to the shared default inventory.

    Unknown actions silently return None and do nothing (legacy behavior).
    """
    if action == "add":
        _default.add(name, qty, price)
    elif action == "remove":
        _default.remove(name, qty)
    elif action == "total":
        return _default.total()
    elif action == "report":
        return _default.report()
    return None
