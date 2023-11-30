from bolinette.data.relational import Repository, repository
from example.entities import Item


@repository(Item)
class ItemRepository(Repository[Item]):
    pass
