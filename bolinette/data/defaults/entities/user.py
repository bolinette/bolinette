from abc import ABC

from bolinette.data import Entity
from bolinette.data.defaults.entities import File, Role


class User(Entity, ABC):
    def __init__(
        self,
        id: int,
        username: str,
        password: str,
        email: str,
        roles: list[Role],
        picture_id: int,
        profile_picture: File,
        timezone: str,
    ):
        self.id = id
        self.username = username
        self.password = password
        self.email = email
        self.roles = roles
        self.picture_id = picture_id
        self.profile_picture = profile_picture
        self.timezone = timezone
