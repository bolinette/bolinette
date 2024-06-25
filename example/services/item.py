from bolinette.core.mapping import Mapper
from bolinette.data.relational import Service, service
from example.entities import Item
from example.repositories import ItemRepository


@service()
class ItemService(Service[Item]):
    def __init__(self, entity: type[Item], repository: ItemRepository, mapper: Mapper) -> None:
        super().__init__(entity, repository, mapper)
