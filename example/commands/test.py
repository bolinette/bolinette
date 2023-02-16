from sqlalchemy import select

from bolinette import command, Injection
from bolinette.ext.data.relational import Repository, EntityManager, SessionManager, get_base

from example.entities import User, Role


@command("test", "Test command")
async def test_command(inject: Injection, entities: EntityManager) -> None:
    await entities.create_all()

    s_inject = inject.get_scoped_session()

    engine = entities._engines[get_base("default")]
    async with engine._session_maker() as session:
        session.add(Role(name="admin"))
        await session.commit()

    async with engine._session_maker() as session:
        r = (await session.execute(select(Role).where(Role.name == "admin"))).scalar_one()
        session.add(User(username="Bob", role_id=r.id))
        session.add(User(username="Jacques", role_id=r.id))
        await session.commit()

    sessions = s_inject.require(SessionManager)
    engine.open_session(sessions)

    user_repo = s_inject.require(Repository[User])
    async for res in user_repo.find_all():
        print(res.username)

    tob = await user_repo.first(select(User).where(User.username == "Bob"), raises=False)
    print(tob)

    bob = await user_repo.get_by_primary(1)
    print(bob)
