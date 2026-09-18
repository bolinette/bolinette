import inspect
from typing import Any, TypeGuard

from escondite import Cache
from muotti import Mapper
from peritype import TWrap, wrap_type
from soupape import AsyncInjector

from bolinette.core import Logger, meta
from bolinette.core.configuration import ConfigSection, CoreConfigSection
from bolinette.web._abstract import WebSocketRequest, WebSocketResponse
from bolinette.web._json import to_json_value
from bolinette.web._utils import get_cls_attrs
from bolinette.web.exceptions import BadRequestError, ForbiddenError, NotFoundError, WebErrorHandler
from bolinette.web.ws._channel import ChannelMessage, WebSocketChannelMeta
from bolinette.web.ws._requests import (
    ChannelRequest,
    ChannelSendRequest,
    ChannelSubscribeRequest,
    ChannelUnsubscribeRequest,
    SocketContent,
)
from bolinette.web.ws._sub import WebSocketSubscription
from bolinette.web.ws._topic import WebSocketTopic, WebSocketTopicMeta


def _is_message(content: Any) -> TypeGuard[ChannelRequest]:
    if not isinstance(content, dict):
        return False
    values: dict[str, Any] = content  # pyright: ignore[reportUnknownVariableType]
    return values.get("action") in ("sub", "unsub", "send", "close")


def _has_channel(content: dict[str, Any]) -> bool:
    return isinstance(content.get("topic"), str) and isinstance(content.get("channel"), str)


def _is_sub_request(content: ChannelRequest) -> TypeGuard[ChannelSubscribeRequest]:
    return _has_channel(dict(content))


def _is_unsub_request(content: ChannelRequest) -> TypeGuard[ChannelUnsubscribeRequest]:
    return _has_channel(dict(content))


def _is_send_request(content: ChannelRequest) -> TypeGuard[ChannelSendRequest[SocketContent]]:
    values = dict(content)
    return _has_channel(values) and "data" in values


class WebSocketHandler:
    def __init__(
        self,
        cache: Cache,
        injector: AsyncInjector,
        logger: "Logger[WebSocketHandler]",
        core_section: ConfigSection[CoreConfigSection],
        mapper: Mapper,
    ) -> None:
        self.injector = injector
        self.logger = logger
        self.core_section = core_section
        self.mapper = mapper
        self.topics: dict[str, _WSTypeBag] = {}
        self.subscriptions: dict[WebSocketResponse, dict[str, set[str]]] = {}
        for cls in cache.get(WebSocketTopicMeta.KEY, hint=type[WebSocketTopic[...]], raises=False):
            topic_meta: WebSocketTopicMeta = meta.get(cls, WebSocketTopicMeta.KEY)
            self.add_topic(topic_meta.name, cls)

    def add_topic(self, name: str, cls: type[WebSocketTopic[...]]) -> None:
        self.topics[name] = _WSTypeBag(wrap_type(cls))

    async def handle(self, request: WebSocketRequest, response: WebSocketResponse) -> None:
        try:
            content = request.json()
            if not _is_message(content):
                raise BadRequestError(
                    "Invalid message, action must be sub, unsub, send or close",
                    "ws.bad_request",
                )
            match content["action"]:
                case "sub":
                    if not _is_sub_request(content):
                        raise BadRequestError("Invalid sub action, must contain topic and channel", "ws.bad_request")
                    await self._subscribe(content, response)
                case "unsub":
                    if not _is_unsub_request(content):
                        raise BadRequestError("Invalid unsub action, must contain topic and channel", "ws.bad_request")
                    await self._unsubscribe(content, response)
                case "send":
                    if not _is_send_request(content):
                        raise BadRequestError(
                            "Invalid send action, must contain topic, channel and data",
                            "ws.bad_request",
                        )
                    await self._send(content, response)
                case "close":
                    await self._close(response)
        except Exception as err:
            self.logger.exception("Error while handling the websocket message")
            _, payload = WebErrorHandler.create_error_payload(err, self.core_section.value.debug)
            await response.send(json=to_json_value(self.mapper, payload))

    async def remove_connection(self, response: WebSocketResponse) -> None:
        await self._close(response)

    async def _subscribe(self, request: ChannelSubscribeRequest, response: WebSocketResponse) -> None:
        topic_name = request["topic"]
        channel_name = request["channel"]
        topic = self._get_topic(topic_name)
        async with self.injector.get_scoped_injector() as scoped:
            topic_instance: WebSocketTopic[...] = await scoped.require(topic.t)
            result = await topic_instance.subscribe(WebSocketSubscription(channel_name))
            if not result:
                raise ForbiddenError(
                    "Subscription rejected",
                    "ws.subscription.rejected",
                    {"topic": topic_name, "channel": channel_name},
                )
            topic.add_subscription(channel_name, response)
            self._add_subscription(response, topic_name, channel_name)

    async def _unsubscribe(self, request: ChannelUnsubscribeRequest, response: WebSocketResponse) -> None:
        topic_name = request["topic"]
        channel_name = request["channel"]
        topic = self._get_topic(topic_name)
        topic.remove_subscription(channel_name, response)
        self._remove_subscription(response, topic_name, channel_name)

    async def _send(self, request: ChannelSendRequest[SocketContent], response: WebSocketResponse) -> None:
        topic = self._get_topic(request["topic"])
        if (channel := topic.match(request["channel"])) is not None:
            async with self.injector.get_scoped_injector() as scoped:
                topic_instance: WebSocketTopic[...] = await scoped.require(topic.t)
                message = ChannelMessage(request["channel"], request["data"], response)
                res = await scoped.call(channel.func, positional_args=[topic_instance, message])
                if inspect.isawaitable(res):
                    await res

    async def _close(self, response: WebSocketResponse) -> None:
        if response in self.subscriptions:
            for topic_name, channels in self.subscriptions[response].items():
                for channel_name in channels:
                    self.topics[topic_name].remove_subscription(channel_name, response)
            del self.subscriptions[response]

    def _get_topic(self, name: str) -> "_WSTypeBag":
        if name not in self.topics:
            raise NotFoundError("Unknown topic", "ws.topic.not_found", {"topic": name})
        return self.topics[name]

    def _add_subscription(self, ws: WebSocketResponse, topic: str, channel: str) -> None:
        if ws not in self.subscriptions:
            self.subscriptions[ws] = {}
        resp_subs = self.subscriptions[ws]
        if topic not in resp_subs:
            resp_subs[topic] = set()
        resp_subs[topic].add(channel)

    def _remove_subscription(self, ws: WebSocketResponse, topic: str, channel: str) -> None:
        resp_subs = self.subscriptions.get(ws)
        if resp_subs is None or topic not in resp_subs or channel not in resp_subs[topic]:
            raise NotFoundError(
                "Subscription not found",
                "ws.subscription.not_found",
                {"topic": topic, "channel": channel},
            )
        resp_subs[topic].remove(channel)


class _WSTypeBag:
    def __init__(self, t: "TWrap[WebSocketTopic[...]]") -> None:
        self.t = t
        self.subs: dict[str, set[WebSocketResponse]] = {}

    def match(self, channel: str) -> "WebSocketChannelMeta[Any, Any, ..., Any] | None":
        for attr in get_cls_attrs(self.t.inner_type).values():
            if meta.has(attr, WebSocketChannelMeta.KEY):
                chan_meta: WebSocketChannelMeta[Any, Any, ..., Any] = meta.get(attr, WebSocketChannelMeta.KEY)
                if chan_meta.pattern.match(channel):
                    return chan_meta
        return None

    def add_subscription(self, channel: str, ws: WebSocketResponse) -> None:
        if channel not in self.subs:
            self.subs[channel] = {ws}
        else:
            self.subs[channel].add(ws)

    def remove_subscription(self, channel: str, ws: WebSocketResponse) -> None:
        if channel not in self.subs or ws not in self.subs[channel]:
            raise NotFoundError("Subscription not found", "ws.subscription.not_found", {"channel": channel})
        self.subs[channel].remove(ws)

    def is_registered(self, channel: str, ws: WebSocketResponse) -> bool:
        return channel in self.subs and ws in self.subs[channel]


class WebSocketContext:
    def __init__(self, handler: WebSocketHandler) -> None:
        self._handler = handler

    async def send(self, topic: str, channel: str, content: SocketContent) -> None:
        if topic not in self._handler.topics:
            return
        topic_t = self._handler.topics[topic]
        if channel not in topic_t.subs:
            return
        for ws in topic_t.subs[channel]:
            await ws.send(json=to_json_value(self._handler.mapper, content))
