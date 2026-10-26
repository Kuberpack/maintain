"""Stock movements for spare parts.

Deduct only when a caller names a spare id. Matching a free-text part name
to a stock row is too easy to get wrong (the sheet repeats similar bearings),
so a replacement that does not carry spare_part_id leaves quantity alone.

Counts are whole pieces: a bearing, a metre of belt, a packet. Fractional
draws are rejected so float math cannot turn 5 on hand into 3.999.
"""

from app.models import SparePart


class OutOfStock(Exception):
    def __init__(self, name: str, on_hand: int, requested: int) -> None:
        self.name = name
        self.on_hand = on_hand
        self.requested = requested
        super().__init__(f"Not enough {name} in stock ({on_hand} on hand, {requested} requested)")


def as_whole_number(value: object) -> int:
    """Accept 4 and 4.0. Reject 1.001, 3.999, and anything that is not a count."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("Quantity must be a whole number")
    if isinstance(value, float) and not value.is_integer():
        raise ValueError("Quantity must be a whole number")
    return int(value)


def deduct_stock(part: SparePart, quantity: int) -> int:
    """Lower qty_on_hand. Returns the quantity actually taken."""
    taken = as_whole_number(quantity)
    if taken < 1:
        raise ValueError("Quantity used must be a whole number of at least 1")
    on_hand = as_whole_number(part.qty_on_hand)
    if on_hand < taken:
        raise OutOfStock(part.name, on_hand, taken)
    part.qty_on_hand = on_hand - taken
    return taken


def restore_stock(part: SparePart, quantity: int) -> None:
    put_back = as_whole_number(quantity)
    if put_back < 1:
        return
    part.qty_on_hand = as_whole_number(part.qty_on_hand) + put_back
