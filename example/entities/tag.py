from abc import ABC

from bolinette.data import Entity

from example import entities


class Tag(Entity, ABC):
    def __init__(
        self,
        id: int,
        name: str,
        parent_id: int,
        parent: "Tag | None",
        labels: list["entities.Label"],
    ):
        self.id = id
        self.name = name
        self.parent_id = parent_id
        self.parent = parent
        self.labels = labels
