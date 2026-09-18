from bolinette.core.extensions import NewProjectHookContext


async def create_example_entity(context: NewProjectHookContext) -> None:
    entities = context.package_folder.add_folder("entities")
    entities.init_package().append(f"from {context.name}.entities.example import Base as Base, Example as Example")
    entities.add_file("example.py").append("""from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from bolinette.data.relational import declarative_base


@declarative_base("default")
class Base(DeclarativeBase):
    pass


class Example(Base):
    __tablename__ = "examples"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]""")


async def create_example_controller(context: NewProjectHookContext) -> None:
    controllers = context.package_folder.add_folder("controllers")
    controllers.init_package().append(
        f"from {context.name}.controllers.example import ExampleController as ExampleController"
    )
    controllers.add_file("example.py").append(f"""from pydantic import BaseModel

from bolinette.api import ApiController, autoroute
from bolinette.web import controller
from {context.name}.entities import Example


class ExamplePayload(BaseModel):
    name: str


class ExamplePatch(BaseModel):
    name: str | None = None


class ExampleResponse(BaseModel):
    id: int
    name: str


@controller("examples")
class ExampleController(ApiController[Example]):
    @autoroute.get_all
    async def get_all(self) -> list[ExampleResponse]: ...

    @autoroute.get_one
    async def get_one(self) -> ExampleResponse: ...

    @autoroute.create
    async def create(self, payload: ExamplePayload) -> ExampleResponse: ...

    @autoroute.update
    async def update(self, payload: ExamplePayload) -> ExampleResponse: ...

    @autoroute.patch
    async def patch(self, payload: ExamplePatch) -> ExampleResponse: ...

    @autoroute.delete
    async def delete(self) -> ExampleResponse: ...""")
