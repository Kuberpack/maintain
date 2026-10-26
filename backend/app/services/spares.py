"""Stock movements for spare parts.

Deduct only when a caller names a spare id. Matching a free-text part name
to a stock row is too easy to get wrong (the sheet repeats similar bearings),
so a replacement that does not carry spare_part_id leaves quantity alone.
"""

from app.models import SparePart


class OutOfStock(Exception):
    def __init__(self, name: str, on_hand: float, requested: float) -> None:
        self.name = name
        self.on_hand = on_hand
        self.requested = requested
        super().__init__(
            f"Not enough {name} in stock ({_format_qty(on_hand)} on hand, {_format_qty(requested)} requested)"
        )


def round_qty(value: float) -> float:
    return round(float(value), 3)


def _format_qty(value: float) -> str:
    rounded = round_qty(value)
    if rounded == int(rounded):
        return str(int(rounded))
    return str(rounded)


def deduct_stock(part: SparePart, quantity: float) -> float:
    """Lower qty_on_hand. Returns the quantity actually taken."""
    taken = round_qty(quantity)
    if taken <= 0:
        raise ValueError("Quantity used must be greater than zero")
    on_hand = round_qty(part.qty_on_hand)
    if on_hand < taken:
        raise OutOfStock(part.name, on_hand, taken)
    part.qty_on_hand = round_qty(on_hand - taken)
    return taken


def restore_stock(part: SparePart, quantity: float) -> None:
    put_back = round_qty(quantity)
    if put_back <= 0:
        return
    part.qty_on_hand = round_qty(round_qty(part.qty_on_hand) + put_back)
