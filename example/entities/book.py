from abc import ABC
from datetime import datetime

from bolinette.data import Entity

from example.entities import Person


class Book(Entity, ABC):
    def __init__(
        self,
        id: int,
        uid: str,
        name: str,
        pages: int,
        price: float,
        publication_date: datetime,
        author_id: int,
        author: Person,
    ):
        self.id = id
        self.uid = uid
        self.name = name
        self.pages = pages
        self.price = price
        self.publication_date = publication_date
        self.author_id = author_id
        self.author = author
