from abc import ABC
from datetime import datetime

from bolinette.data import Entity

from example.entities import User


class Trace(Entity, ABC):
    def __init__(
        self,
        id: int,
        name: str,
        visits: int,
        last_visit: datetime,
        user_id: int,
        user: User,
    ):
        self.id = id
        self.name = name
        self.visits = visits
        self.last_visit = last_visit
        self.user_id = user_id
        self.user = user
