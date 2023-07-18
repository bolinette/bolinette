from typing import Callable, Awaitable

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from bolinette.core import command
from bolinette.core.injection import Injection
from bolinette.data.relational import Repository, EntityManager, SessionManager

from example.entities import User, Role


@command("test", "Test command")
async def test_command(inject: Injection, entities: EntityManager) -> None:
    await entities.create_all()

    async def create_role(role_repo: Repository[Role]):
        role_repo.add(Role(name="admin"))

    async def create_users(role_repo: Repository[Role], user_repo: Repository[User]):
        r = await role_repo.first(select(Role).where(Role.name == "admin"))
        user_repo.add(User(username="Bob", role_id=r.id))
        user_repo.add(User(username="Jacques", role_id=r.id))

    async def select_users(user_repo: Repository[User]):
        async for user in user_repo.iterate(select(User).options(selectinload(User.role))):
            print(user.username, user.role.name)

    async def run_in_scope(func: Callable[..., Awaitable[None]], *, commit: bool = False):
        s_inject = inject.get_scoped_session()
        sessions = s_inject.require(SessionManager)
        entities.open_sessions(sessions)
        await s_inject.call(func)
        if commit:
            await sessions.commit()

    await run_in_scope(create_role, commit=True)
    await run_in_scope(create_users, commit=True)
    await run_in_scope(select_users)
