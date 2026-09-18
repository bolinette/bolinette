from collections.abc import Callable, Sequence
from typing import Any, override

from escondite import Cache
from soupape import ServiceCollection, injectable

from bolinette.core import CoreExtension, meta
from bolinette.core.commands import command
from bolinette.core.configuration import config_section
from bolinette.core.extensions import Extension, NewProjectHook
from bolinette.web._asgi import AsgiApplication
from bolinette.web._commands import new_encryption_key, new_rsa_key
from bolinette.web._config import BlntAuthOptions
from bolinette.web._controller import ControllerMeta
from bolinette.web._middleware import MiddlewareBag
from bolinette.web._resources import WebResources
from bolinette.web._scaffold import create_controllers_package, create_server_file
from bolinette.web._utils import get_cls_attrs
from bolinette.web.auth._blntauth import (
    BLNT_AUTH_SECTION_NAME,
    BlntAuthSection,
    BolinetteAuthProvider,
    register_blnt_auth,
)
from bolinette.web.auth._middleware import Authenticated
from bolinette.web.auth._provider import AuthProviderMeta, AuthProviders, auth_provider
from bolinette.web.ws._handler import WebSocketContext, WebSocketHandler
from bolinette.web.ws._topic import WebSocketTopic, WebSocketTopicMeta


def _options_resolver(options: BlntAuthOptions) -> Callable[[], BlntAuthOptions]:
    def _resolve() -> BlntAuthOptions:
        return options

    return _resolve


def _iter_bags(ctrl_cls: type[Any]) -> "Sequence[MiddlewareBag]":
    bags: list[MiddlewareBag] = []
    if meta.has(ctrl_cls, MiddlewareBag.KEY):
        ctrl_bag: MiddlewareBag = meta.get(ctrl_cls, MiddlewareBag.KEY)
        bags.append(ctrl_bag)
    for attribute in get_cls_attrs(ctrl_cls).values():
        if not callable(attribute):
            continue
        if meta.has(attribute, MiddlewareBag.KEY):
            route_bag: MiddlewareBag = meta.get(attribute, MiddlewareBag.KEY)
            bags.append(route_bag)
    return bags


class WebExtension(Extension):
    name = "web"
    dependencies: Sequence[type[Extension]] = (CoreExtension,)

    def __init__(self, *, blnt_auth: BlntAuthOptions | None = None) -> None:
        self._blnt_auth = blnt_auth

    @override
    def get_new_project_hooks(self) -> Sequence[NewProjectHook]:
        return (create_server_file, create_controllers_package)

    @override
    def register_services(self, services: ServiceCollection, cache: Cache) -> None:
        injectable.singleton(WebResources, cache=cache)
        injectable.singleton(AsgiApplication, cache=cache)
        injectable.singleton(WebSocketHandler, cache=cache)
        injectable.singleton(WebSocketContext, cache=cache)
        injectable.singleton(AuthProviders, cache=cache)

        command(new_rsa_key, "auth new rsa", "Creates a new RSA key pair", cache=cache, run_startup=False)
        command(
            new_encryption_key,
            "auth new encrypt",
            "Creates a new encryption key",
            cache=cache,
            run_startup=False,
        )

        registered: set[type[Any]] = {Authenticated}
        services.add_scoped(Authenticated)

        if self._blnt_auth is not None:
            config_section(BlntAuthSection, BLNT_AUTH_SECTION_NAME)
            services.add_singleton(_options_resolver(self._blnt_auth))
            auth_provider(cache=cache)(BolinetteAuthProvider)
            register_blnt_auth(services, cache)

        for provider_cls in cache.get(AuthProviderMeta.KEY, hint=type[Any], raises=False):
            if provider_cls not in registered:
                registered.add(provider_cls)
                services.add_singleton(provider_cls)

        for ctrl_cls in cache.get(ControllerMeta.KEY, hint=type[Any], raises=False):
            if ctrl_cls in registered:
                continue
            registered.add(ctrl_cls)
            services.add_scoped(ctrl_cls)
            for bag in _iter_bags(ctrl_cls):
                for mdlw_type in (*bag.added, *bag.removed):
                    mdlw_cls: type[Any] = mdlw_type.origin
                    if mdlw_cls in registered:
                        continue
                    registered.add(mdlw_cls)
                    services.add_scoped(mdlw_cls)

        for topic_cls in cache.get(WebSocketTopicMeta.KEY, hint=type[WebSocketTopic[...]], raises=False):
            if topic_cls not in registered:
                registered.add(topic_cls)
                services.add_scoped(topic_cls)
