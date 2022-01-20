from abc import ABC

from bolinette.data import Entity

from example import entities


class Person(Entity, ABC):
    def __init__(self, id: int, uid: str, first_name: str, last_name: str, book: list['entities.Book']):
        self.id = id
        self.uid = uid
        self.first_name = first_name
        self.last_name = last_name
