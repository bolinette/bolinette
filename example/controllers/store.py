from typing import Annotated

from bolinette.core.mapping import Mapper
from bolinette.web import Payload, controller, get, post
from example.controllers.payloads import ItemPayload
from example.controllers.responses import ItemResponse
from example.entities import Item
from example.repositories import ItemRepository


@controller("store")
class StoreController:
    def __init__(self, repo: ItemRepository, mapper: Mapper) -> None:
        self.repo = repo
        self.mapper = mapper

    @get("items")
    async def get_all(self) -> list[ItemResponse]:
        return self.mapper.map(list[Item], list[ItemResponse], [i async for i in self.repo.find_all()])

    @post("item")
    async def create(self, item_payload: Annotated[ItemPayload, Payload()]) -> ItemResponse:
        item = Item(
            id=item_payload.id,
            name=item_payload.name,
            price=item_payload.price,
            quantity=item_payload.quantity,
        )
        self.repo.add(item)
        return self.mapper.map(Item, ItemResponse, item)
