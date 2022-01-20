from abc import ABC

from bolinette.data import Entity


class File(Entity, ABC):
    def __init__(self, id: int, key: str, name: str, mime: str):
        self.id = id
        self.key = key
        self.name = name
        self.mime = mime
