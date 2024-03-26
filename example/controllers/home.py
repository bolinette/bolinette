from typing import Annotated

from bolinette.web import Payload, controller, get, post
from example.controllers.payloads import HomeHelloPayload
from example.controllers.responses import HomeResponse


@controller("")
class HomeController:
    @get("")
    async def home(self) -> HomeResponse:
        return HomeResponse("Bolinette example app", "0.0.1")

    @get("echo/{param:\\d+}")
    async def echo_param_int(self, param: int) -> str:
        return str(param + 1)

    @get("echo/{param}")
    async def echo_param(self, param: str) -> str:
        return param

    @get("echo/{param}/1")
    async def echo_param_1(self, param: str) -> str:
        return param + "/1"

    @get("echo/{param}/2")
    async def echo_param_2(self, param: str) -> str:
        return param + "/2"

    @post("hello")
    async def hello(self, payload: Annotated[HomeHelloPayload, Payload]) -> str:
        return f"Hello {payload.firstname} {payload.lastname}!"
