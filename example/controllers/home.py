from bolinette.web import controller
from bolinette.web.route import get
from example.controllers.responses import HomeResponse


@controller("")
class HomeController:
    @get("")
    async def home(self) -> HomeResponse:
        return HomeResponse("Bolinette example app", "0.0.1")
