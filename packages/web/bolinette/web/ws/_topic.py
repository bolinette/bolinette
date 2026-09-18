from collections.abc import Callable
from typing import ClassVar, Protocol

from escondite import Cache

from bolinette.core import meta
from bolinette.web.ws._sub import WebSocketSubResult, WebSocketSubscription


class WebSocketTopic[**SubP](Protocol):
    async def subscribe(
        self,
        sub: WebSocketSubscription,
        /,
        *args: SubP.args,
        **kwargs: SubP.kwargs,
    ) -> WebSocketSubResult: ...


class WebSocketTopicMeta:
    KEY: ClassVar[str] = "__blnt_web_ws_topic_meta__"

    def __init__(self, name: str) -> None:
        self.name = name


def topic[**SubP](
    name: str,
    *,
    cache: Cache | None = None,
) -> Callable[[type[WebSocketTopic[SubP]]], type[WebSocketTopic[SubP]]]:
    def decorator(cls: type[WebSocketTopic[SubP]]) -> type[WebSocketTopic[SubP]]:
        meta.set(cls, WebSocketTopicMeta.KEY, WebSocketTopicMeta(name))
        Cache.with_fallback(cache).add(WebSocketTopicMeta.KEY, cls)
        return cls

    return decorator
