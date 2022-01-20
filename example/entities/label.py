from abc import ABC

from bolinette.data import Entity

from example.entities import Tag


class Label(Entity, ABC):
    def __init__(self, tag_id: int, id: int, name: str, tag: Tag):
        self.tag_id = tag_id
        self.id = id
        self.name = name
        self.tag = tag
