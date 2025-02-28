from collections.abc import Callable
from typing import Any, Protocol

from bolinette.core import Cache, __user_cache__
from bolinette.core.injection import Injection, post_init
from bolinette.web.exceptions import UnauthorizedError


class AuthProvider(Protocol):
    issuer: str

    def validate(self, token: str) -> dict[str, Any]: ...


class NotSupportedTokenError(Exception): ...


def auth_provider[T: AuthProvider](*, cache: Cache | None = None) -> Callable[[type[T]], type[T]]:
    def decorator(cls: type[T]) -> type[T]:
        (cache or __user_cache__).add(AuthProvider, cls)
        return cls

    return decorator


class AuthProviders:
    def __init__(self, inject: Injection) -> None:
        self.providers: dict[str, AuthProvider]
        self.inject = inject

    @post_init
    def _init_providers(self, cache: Cache) -> None:
        providers: dict[str, AuthProvider] = {}
        for cls in cache.get(AuthProvider, hint=type[AuthProvider], raises=False):
            provider = self.inject.instantiate(cls)
            self.inject.add_singleton(cls, instance=provider)
            providers[provider.issuer] = provider
        self.providers = providers

    def add_provider(self, cls: type[AuthProvider]) -> None:
        provider = self.inject.instantiate(cls)
        self.inject.add_singleton(cls, instance=provider)
        self.providers[provider.issuer] = provider

    def validate(self, token: str) -> Any:
        for _, provider in self.providers.items():
            try:
                return provider.validate(token)
            except NotSupportedTokenError:
                pass
        raise UnauthorizedError("Auth token could not be verified", "auth.token.unverified")
