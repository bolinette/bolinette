from abc import ABC

from bolinette.data import Entity


class Library(Entity, ABC):
    def __init__(self, id: int, key: str, name: str, address: str):
        self.id = id
        self.key = key
        self.name = name
        self.address = address
