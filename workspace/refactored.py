from dataclasses import dataclass

Number = int | float


@dataclass
class Item:
    """A stocked product."""
    qty: Number
    price: Number


class Inventory:
    """In-memory inventory. Insertion-ordered by item name."""

    def __init__(self) -> None:
        self._items: dict[str, Item] = {}

    def add_item(self, name: str, qty: Number = 0, price: Number = 0) -> None:
        """New name: store Item(qty, price) as given (even qty<=0).
        Existing name: qty += qty; the supplied price is IGNORED (existing price kept).
        No deletion on add. Returns None."""
        existing = self._items.get(name)
        if existing is not None:
            existing.qty = existing.qty + qty
        else:
            self._items[name] = Item(qty, price)

    def remove_item(self, name: str, qty: Number = 0) -> None:
        """Missing name: silent no-op. Otherwise qty -= qty; if the result <= 0,
        delete the item (checked on every remove, including qty=0). Returns None."""
        item = self._items.get(name)
        if item is None:
            return None
        item.qty = item.qty - qty
        if item.qty <= 0:
            del self._items[name]
        return None

    def total_value(self) -> Number:
        """Sum of qty*price over all items; returns int 0 when empty."""
        total: Number = 0
        for item in self._items.values():
            total = total + item.qty * item.price
        return total

    def report(self) -> str:
        """One line per item in insertion order."""
        return "".join(
            f"{name}: {item.qty} @ ${item.price}\n"
            for name, item in self._items.items()
        )


_default_inventory = Inventory()


def do_stuff(action, name, qty=0, price=0):
    """Legacy facade. Dispatches on `action` to _default_inventory."""
    inventory = _default_inventory
    if action == "add":
        inventory.add_item(name, qty, price)
        return None
    if action == "remove":
        inventory.remove_item(name, qty)
        return None
    if action == "total":
        return inventory.total_value()
    if action == "report":
        return inventory.report()
    return None
