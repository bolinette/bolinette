from dataclasses import dataclass


@dataclass(init=False)
class ItemResponse:
    id: int
    name: str
    price: float
    quantity: int
