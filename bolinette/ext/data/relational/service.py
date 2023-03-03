from typing import Generic, TypeVar

from bolinette.ext.data.relational import DeclarativeBase, Repository

EntityT = TypeVar("EntityT", bound=DeclarativeBase)


class Service(Generic[EntityT]):
    def __init__(self, repository: Repository[EntityT]) -> None:
        self._repository = repository
