from sqlalchemy.orm import Mapped, mapped_column

from bolinette.data.relational import entity, get_base


@entity(entity_key="id")
class Item(get_base("default")):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column()
    price: Mapped[float] = mapped_column()
    quantity: Mapped[int] = mapped_column()
