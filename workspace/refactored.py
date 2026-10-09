from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Item:
    """A stock entry: quantity and unit price."""
    qty: float
    price: float


class Inventory:
    """In-memory inventory keeping insertion order."""

    def __init__(self) -> None:
        self._items: dict[str, Item] = {}

    def add(self, name: str, qty: float = 0, price: float = 0) -> None:
        """Add stock. Existing items keep their original price."""
        if name in self._items:
            self._items[name].qty = self._items[name].qty + qty
        else:
            self._items[name] = Item(qty, price)

    def remove(self, name: str, qty: float = 0) -> None:
        """Remove stock; delete item if quantity drops to <= 0. Missing: no-op."""
        item = self._items.get(name)
        if item is None:
            return
        item.qty = item.qty - qty
        if item.qty <= 0:
            del self._items[name]

    def total_value(self) -> float:
        """Sum of qty * price over all items (int 0 when empty)."""
        return sum((i.qty * i.price for i in self._items.values()), 0)

    def report(self) -> str:
        """One line per item in insertion order."""
        return "".join(
            f"{name}: {str(i.qty)} @ ${str(i.price)}\n"
            for name, i in self._items.items()
        )

    def __contains__(self, name: str) -> bool:
        return name in self._items

    def quantity(self, name: str) -> Optional[float]:
        """Quantity of an item, or None if absent."""
        item = self._items.get(name)
        return None if item is None else item.qty


_default = Inventory()


def do_stuff(action, name, qty=0, price=0):
    """Backward-compatible shim dispatching on action strings."""
    inv = _default
    if action == "add":
        inv.add(name, qty, price)
        return None
    if action == "remove":
        inv.remove(name, qty)
        return None
    if action == "total":
        return inv.total_value()
    if action == "report":
        return inv.report()
    return None
