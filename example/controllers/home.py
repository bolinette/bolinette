from bolinette.web import controller, payload
from bolinette.web.route import get, post
from example.controllers.payloads import HomeHelloPayload
from example.controllers.responses import HomeResponse


@controller("")
class HomeController:
    @get("")
    async def home(self) -> HomeResponse:
        return HomeResponse("Bolinette example app", "0.0.1")

    @post("hello")
    async def hello(self, payload: HomeHelloPayload = payload()) -> str:
        return f"Hello {payload.firstname} {payload.lastname}!"
