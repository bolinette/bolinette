from bolinette.web import controller, get


@controller("home")
class HomeController:
    # @get("")
    # async def home(self) -> HomeResponse:
    #     return HomeResponse("Bolinette example app", "0.0.1")

    @get("route/{id:int}/params")
    def test_route_p(self, id: int):
        return f"{id}: params"

    @get("route/{id:int}/params/{param}/1")
    def test_route(self, id: int, param: str):
        return f"{id}: {param}: 1"

    @get("route/{id:int}")
    def test_route_short(self, id: int):
        return f"{id}"

    @get("route/{id:int}/params/{param}/2")
    def test_route_2(self, id: int, param: str):
        return f"{id}: {param}: 2"

    @get("route/{id:int}/params/{param:float}/3")
    def test_route_3(self, id: int, param: float):
        return f"{id}: {param}: float"

    @get("route/{id:int}/params/{param:int}/3")
    def test_route_3f(self, id: int, param: int):
        return f"{id}: {param}: int"

    # @post("hello")
    # async def hello(self, payload: Annotated[HomeHelloPayload, Payload]) -> str:
    #     return f"Hello {payload.firstname} {payload.lastname}!"
