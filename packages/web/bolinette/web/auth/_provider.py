from collections.abc import Callable
from typing import Any, ClassVar, Protocol

from escondite import Cache
from soupape import AsyncInjector

from bolinette.web.exceptions import UnauthorizedError


class AuthProvider(Protocol):
    issuer: str

    def validate(self, token: str) -> dict[str, Any]: ...


class NotSupportedTokenError(Exception): ...


class AuthProviderMeta:
    KEY: ClassVar[str] = "__blnt_web_auth_provider__"


def auth_provider[T: AuthProvider](*, cache: Cache | None = None) -> Callable[[type[T]], type[T]]:
    def decorator(cls: type[T]) -> type[T]:
        Cache.with_fallback(cache).add(AuthProviderMeta.KEY, cls)
        return cls

    return decorator


class AuthProviders:
    def __init__(self, cache: Cache, injector: AsyncInjector) -> None:
        self._injector = injector
        self._classes: list[type[AuthProvider]] = list(
            cache.get(AuthProviderMeta.KEY, hint=type[AuthProvider], raises=False)
        )
        self._providers: dict[str, AuthProvider] | None = None

    def add_provider(self, cls: type[AuthProvider]) -> None:
        if cls not in self._classes:
            self._classes.append(cls)
        self._providers = None

    async def get_providers(self) -> dict[str, AuthProvider]:
        if self._providers is None:
            providers: dict[str, AuthProvider] = {}
            for cls in self._classes:
                provider: AuthProvider = await self._injector.require(cls)
                providers[provider.issuer] = provider
            self._providers = providers
        return self._providers

    async def validate(self, token: str) -> Any:
        for provider in (await self.get_providers()).values():
            try:
                return provider.validate(token)
            except NotSupportedTokenError:
                pass
        raise UnauthorizedError("Auth token could not be verified", "auth.token.unverified")
