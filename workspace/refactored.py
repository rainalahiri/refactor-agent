from dataclasses import dataclass


@dataclass
class _Item:
    qty: float
    price: float


class Inventory:
    """Simple insertion-ordered inventory keyed by item name.

    No validation is performed. Quirks preserved from the legacy module:
    price is ignored when restocking an existing item, and removing more
    than is available silently deletes the item.
    """

    def __init__(self) -> None:
        self._items: dict = {}

    def add(self, name, qty=0, price=0) -> None:
        """New name -> store _Item(qty, price). Existing name -> qty += qty;
        the price is NOT updated. Items are never deleted on add."""
        item = self._items.get(name)
        if item is not None:
            item.qty += qty
        else:
            self._items[name] = _Item(qty, price)

    def remove(self, name, qty=0) -> None:
        """Missing name -> silent no-op. Otherwise subtract qty; if the
        result is <= 0 the item is deleted (including over-removal)."""
        item = self._items.get(name)
        if item is None:
            return
        item.qty -= qty
        if item.qty <= 0:
            del self._items[name]

    def total(self):
        """Sum of qty*price over all items; int 0 when empty."""
        t = 0
        for item in self._items.values():
            t += item.qty * item.price
        return t

    def report(self) -> str:
        """One line per item in insertion order: "name: qty @ $price\\n".

        Non-str names raise TypeError (as in the legacy implementation).
        """
        return "".join(
            name + ": " + str(item.qty) + " @ $" + str(item.price) + "\n"
            for name, item in self._items.items()
        )

    def quantity(self, name):
        """Return the qty, or None if absent."""
        item = self._items.get(name)
        return None if item is None else item.qty

    def __contains__(self, name) -> bool:
        return name in self._items

    def __len__(self) -> int:
        return len(self._items)


_default_inventory = Inventory()


def reset_default_inventory() -> None:
    """Replace the module-level default inventory with a fresh one."""
    global _default_inventory
    _default_inventory = Inventory()


def do_stuff(action, name, qty=0, price=0):
    """Backward-compatible facade over the default inventory.

    'add' / 'remove' return None; 'total' / 'report' return their values;
    any other action is a silent no-op returning None.
    """
    inventory = _default_inventory
    if action == "add":
        inventory.add(name, qty, price)
        return None
    elif action == "remove":
        inventory.remove(name, qty)
        return None
    elif action == "total":
        return inventory.total()
    elif action == "report":
        return inventory.report()
    return None
