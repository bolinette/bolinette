from collections.abc import Awaitable, Callable
from typing import Any

from soupape import AsyncInjector

from bolinette.web._abstract import Request
from bolinette.web._utils import instance_resolver
from bolinette.web.auth._provider import AuthProviders
from bolinette.web.exceptions import BadRequestError, UnauthorizedError


class Authenticated:
    def __init__(self, injector: AsyncInjector, request: Request, providers: AuthProviders) -> None:
        self.injector = injector
        self.request = request
        self.providers = providers

    def options(self) -> None:
        pass

    async def handle(self, next: Callable[[], Awaitable[Any]]) -> Any:
        if not self.request.has_header("authorization"):
            raise UnauthorizedError("Unauthorized access to this resource", "unauthorized")
        token = self.request.get_header("authorization")
        if not token.startswith("Bearer "):
            raise BadRequestError("Auth token has to start with 'Bearer '", "auth.token.bad_format")
        user_info: Any = await self.providers.validate(token[len("Bearer ") :])
        self.injector.services.add_scoped(instance_resolver(type(user_info), user_info))
        return await next()
