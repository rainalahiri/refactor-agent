"""Shipping cost calculator."""
from dataclasses import dataclass


@dataclass(frozen=True)
class RateCard:
    """Pricing parameters for a shipping zone."""
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


def _base_cost(card: RateCard, weight: float, distance: float) -> float:
    """Base + per-kg + per-distance cost for the given rate card."""
    return card.base + weight * card.per_kg + distance * card.per_distance


def _apply_express(card: RateCard, cost: float) -> float:
    """Apply express multiplier, then express surcharge."""
    return cost * card.express_multiplier + card.express_surcharge


def _apply_member_discount(cost: float) -> float:
    """Apply tiered member discount (strictly greater than threshold -> high)."""
    if cost > MEMBER_DISCOUNT_THRESHOLD:
        rate = MEMBER_DISCOUNT_HIGH
    else:
        rate = MEMBER_DISCOUNT_LOW
    return cost - cost * rate


def _apply_heavy_surcharge(cost: float, weight: float) -> float:
    """Add flat surcharge when weight is strictly above the threshold."""
    if weight > HEAVY_WEIGHT_THRESHOLD:
        return cost + HEAVY_SURCHARGE
    return cost


def calculate_shipping_cost(weight: float, distance: float, *,
                            express: bool, international: bool,
                            member: bool) -> float:
    """Compute the shipping cost.

    Order: base, express, member discount, heavy surcharge, round to 2 places.
    """
    card = INTERNATIONAL if international else DOMESTIC
    cost = _base_cost(card, weight, distance)
    if express:
        cost = _apply_express(card, cost)
    if member:
        cost = _apply_member_discount(cost)
    cost = _apply_heavy_surcharge(cost, weight)
    return round(cost, 2)


def ship(w, dist, express, intl, member):
    """Backward-compatible positional wrapper around calculate_shipping_cost."""
    return calculate_shipping_cost(w, dist, express=express,
                                   international=intl, member=member)
