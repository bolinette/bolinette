from bolinette.api import ApiController, autoroute
from bolinette.web import controller
from example.controllers.payloads import ItemPayload
from example.controllers.responses import ItemResponse
from example.entities import Item


@controller("store")
class StoreController(ApiController[Item]):
    @autoroute.get_all(ItemResponse)
    async def get_all(self) -> None: ...

    @autoroute.get_one(ItemResponse)
    async def get_one(self) -> None: ...

    @autoroute.create(ItemPayload, ItemResponse)
    async def create(self) -> None: ...

    @autoroute.update(ItemPayload, ItemResponse)
    async def update(self) -> None: ...

    @autoroute.patch(ItemPayload, ItemResponse)
    async def patch(self) -> None: ...

    @autoroute.delete(ItemResponse)
    async def delete(self) -> None: ...
