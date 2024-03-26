from collections.abc import Callable
from typing import Protocol

from bolinette.core import Cache, __user_cache__, meta
from bolinette.web.ws import WebSocketSubResult, WebSocketSubscription


class WebSocketTopic[**SubP](Protocol):
    async def subscribe(
        self,
        sub: WebSocketSubscription,
        /,
        *args: SubP.args,
        **kwargs: SubP.kwargs,
    ) -> WebSocketSubResult: ...


class WebSocketTopicMeta:
    def __init__(self, name: str) -> None:
        self.name = name


def topic[**SubP](
    name: str, *, cache: Cache | None = None
) -> Callable[[type[WebSocketTopic[SubP]]], type[WebSocketTopic[SubP]]]:
    def decorator(cls: type[WebSocketTopic[SubP]]) -> type[WebSocketTopic[SubP]]:
        (cache or __user_cache__).add(WebSocketTopic, cls)
        meta.set(cls, WebSocketTopicMeta(name))
        return cls

    return decorator
