from typing import Any, Literal, TypedDict

type SocketContent = int | float | bool | str | list[SocketContent] | dict[str, SocketContent]


class WebSocketSubscribeRequest(TypedDict):
    action: Literal["sub"]
    topic: str
    channel: str


class WebSocketUnsubscribeRequest(TypedDict):
    action: Literal["unsub"]
    topic: str
    channel: str


class WebSocketSendRequest[D: SocketContent](TypedDict):
    action: Literal["send"]
    topic: str
    channel: str
    data: D


class WebSocketCloseRequest(TypedDict):
    action: Literal["close"]


type WebSocketRequest = (
    WebSocketSubscribeRequest | WebSocketUnsubscribeRequest | WebSocketSendRequest[Any] | WebSocketCloseRequest
)
