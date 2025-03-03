from bolinette.core import Bolinette, Cache, startup


async def test_start_bolinette() -> None:
    cache = Cache()
    blnt = Bolinette(cache=cache)

    order: list[str] = []

    def test_startup() -> None:
        order.append("startup")

    startup(cache=cache)(test_startup)

    await blnt.build().startup()

    assert order == ["startup"]
