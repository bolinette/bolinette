from abc import ABC

from bolinette.data import Entity
from bolinette.data.defaults import entities


class Role(Entity, ABC):
    def __init__(self, id: int, name: str, users: "entities.User"):
        self.id = id
        self.name = name
        self.users = users
