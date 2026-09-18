import re
from collections.abc import Callable
from typing import ClassVar, Concatenate

from bolinette.core import meta
from bolinette.web._abstract import WebSocketResponse
from bolinette.web.ws._requests import SocketContent
from bolinette.web.ws._topic import WebSocketTopic


class ChannelMessage[T: SocketContent]:
    def __init__(self, channel: str, value: T, response: WebSocketResponse) -> None:
        self.channel = channel
        self.type = type(value)
        self.value = value
        self.response = response


type ChannelFunc[W: WebSocketTopic[...], M: SocketContent, **P, T] = Callable[Concatenate[W, ChannelMessage[M], P], T]


class WebSocketChannelMeta[W: WebSocketTopic[...], M: SocketContent, **P, T]:
    KEY: ClassVar[str] = "__blnt_web_ws_channel_meta__"

    def __init__(self, pattern: str, func: ChannelFunc[W, M, P, T]) -> None:
        self.pattern = re.compile(pattern)
        self.func = func


def channel[W: WebSocketTopic[...], M: SocketContent, **P, T](
    pattern: str,
    /,
) -> Callable[[ChannelFunc[W, M, P, T]], ChannelFunc[W, M, P, T]]:
    def decorator(func: ChannelFunc[W, M, P, T]) -> ChannelFunc[W, M, P, T]:
        meta.set(func, WebSocketChannelMeta.KEY, WebSocketChannelMeta(pattern, func))
        return func

    return decorator
