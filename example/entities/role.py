from typing import Annotated

from bolinette.ext.data import Entity, PrimaryKey, entity


@entity()
class Role(Entity):
    id: Annotated[int, PrimaryKey()]
    name: str
