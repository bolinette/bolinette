from typing import Any, Literal, TypedDict

type SocketContent = int | float | bool | str | list[SocketContent] | dict[str, SocketContent]


class ChannelSubscribeRequest(TypedDict):
    action: Literal["sub"]
    topic: str
    channel: str


class ChannelUnsubscribeRequest(TypedDict):
    action: Literal["unsub"]
    topic: str
    channel: str


class ChannelSendRequest[D: SocketContent](TypedDict):
    action: Literal["send"]
    topic: str
    channel: str
    data: D


class ChannelCloseRequest(TypedDict):
    action: Literal["close"]


type ChannelRequest = (
    ChannelSubscribeRequest | ChannelUnsubscribeRequest | ChannelSendRequest[Any] | ChannelCloseRequest
)
