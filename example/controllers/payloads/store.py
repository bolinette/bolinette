from dataclasses import dataclass


@dataclass(init=False)
class ItemPayload:
    id: int
    name: str
    price: float
    quantity: int
