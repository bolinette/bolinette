from typing import Annotated

from bolinette.ext.data import Entity, PrimaryKey, ForeignKey, ManyToOne, entity

from example.entities import Role


@entity()
class User(Entity):
    id: Annotated[int, PrimaryKey()]
    username: str

    role_id: Annotated[int, ForeignKey(Role)]
    role: Annotated[Role, ManyToOne(['role_id'])]
