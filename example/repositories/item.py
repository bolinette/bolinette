from bolinette.data.relational import Repository, repository
from example.entities import Item


@repository()
class ItemRepository(Repository[Item]):
    pass
