from typing import TYPE_CHECKING

from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bolinette.data.relational import entity, get_base

if TYPE_CHECKING:
    from example.entities import User


@entity()
class Role(get_base("default")):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column()

    users: Mapped[list["User"]] = relationship(back_populates="role")

    __table_args__ = (UniqueConstraint("name"),)
