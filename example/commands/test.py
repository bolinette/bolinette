from collections.abc import Awaitable, Callable
from typing import Annotated, Literal

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from bolinette.core.command import Argument, command
from bolinette.core.injection import Injection
from bolinette.data.relational import EntityManager, Repository
from example.entities import Role, User


@command("test entities", "Test command")
async def test_command(
    inject: Injection,
    entities: EntityManager,
    count: Annotated[Literal[1, 2, 3, 4], Argument("option")] = 2,
) -> None:
    await entities.create_all()

    async def create_role(role_repo: Repository[Role]):
        role_repo.add(Role(name="admin"))

    async def create_users(role_repo: Repository[Role], user_repo: Repository[User]):
        r = await role_repo.first(select(Role).where(Role.name == "admin"))
        for name in ["Bob", "Jacques", "Michel", "Constantin"][:count]:
            user_repo.add(User(username=name, role_id=r.id))

    async def select_users(user_repo: Repository[User]):
        async for user in user_repo.iterate(select(User).options(selectinload(User.role))):
            print(user.username, user.role.name)

    async def run_in_scope(func: Callable[..., Awaitable[None]]):
        async with inject.get_async_scoped_session() as s_inject:
            await s_inject.call(func)

    await run_in_scope(create_role)
    await run_in_scope(create_users)
    await run_in_scope(select_users)
