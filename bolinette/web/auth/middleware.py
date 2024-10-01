from collections.abc import Awaitable, Callable
from typing import Any

from bolinette.core.injection import Injection
from bolinette.web.abstract import Request
from bolinette.web.auth import AuthProviders
from bolinette.web.exceptions import BadRequestError, UnauthorizedError


class Authenticated:
    def __init__(self, inject: Injection, request: Request, providers: AuthProviders) -> None:
        self.inject = inject
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
        user_info: Any = self.providers.validate(token[len("Bearer ") :])
        self.inject.add_scoped(type(user_info), instance=user_info)  # pyright: ignore[reportUnknownArgumentType]
        return await next()
