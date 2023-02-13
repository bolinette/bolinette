from sqlalchemy import select

from bolinette import command, Injection
from bolinette.ext.data import DatabaseManager, Repository
from bolinette.ext.data.sessions import SessionManager

from example.entities import User, Role


@command("test", "Test command")
async def test_command(inject: Injection, database: DatabaseManager) -> None:
    engine = database.get_engine("default")

    await engine.create_all()
    role_cls = engine.get_definition(Role)
    usr_cls = engine.get_definition(User)

    s_inject = inject.get_scoped_session()

    async with engine._session_maker() as session:
        session.add(role_cls(name="admin"))
        await session.commit()

    sessions = s_inject.require(SessionManager)
    engine.open_session(sessions)

    async with engine._session_maker() as session:
        r = (await session.execute(select(role_cls).where(role_cls.name == "admin"))).scalar_one()
        session.add(usr_cls(username="Bob", role_id=r.id))
        session.add(usr_cls(username="Jacques", role_id=r.id))
        await session.commit()

    user_repo = s_inject.require(Repository[User])
    async for res in user_repo.find_all():
        print(res.username)
    async for res in user_repo.query().where(lambda u: u.username == "Bob").include(lambda u: u.role).all():
        print(res.id, res.username, res.role.name)
