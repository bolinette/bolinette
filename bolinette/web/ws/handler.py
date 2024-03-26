import inspect
import json
from typing import Any, TypeGuard

from bolinette.core import Cache, Logger, meta
from bolinette.core.environment import CoreSection
from bolinette.core.injection import Injection, init_method
from bolinette.core.mapping.json import JsonObjectEncoder
from bolinette.core.types import Type, TypeChecker
from bolinette.core.utils import AttributeUtils
from bolinette.web.abstract import WebSocketRequest, WebSocketResponse
from bolinette.web.exceptions import BadRequestError, NotFoundError, WebErrorHandler
from bolinette.web.ws import ChannelMessage, WebSocketSubscription, WebSocketTopic
from bolinette.web.ws.channel import WebSocketChannelMeta
from bolinette.web.ws.requests import (
    ChannelRequest,
    ChannelSendRequest,
    ChannelSubscribeRequest,
    ChannelUnsubscribeRequest,
    SocketContent,
)
from bolinette.web.ws.topic import WebSocketTopicMeta


class WebSocketHandler:
    def __init__(
        self,
        logger: "Logger[WebSocketHandler]",
        checker: TypeChecker,
        inject: Injection,
        core_section: CoreSection,
    ) -> None:
        self.logger = logger
        self.checker = checker
        self.topics: dict[str, _WSTypeBag]
        self.inject = inject
        self.core_section = core_section
        self.subscriptions: dict[WebSocketResponse, dict[str, set[str]]] = {}

    @init_method
    def _init_topics(self, cache: Cache) -> None:
        self.topics = {}
        for cls in cache.get(WebSocketTopic, hint=type[WebSocketTopic[...]], raises=False):
            topic_meta = meta.get(cls, WebSocketTopicMeta)
            self.add_topic(topic_meta.name, cls)

    @init_method
    def _add_context_to_inject(self) -> None:
        self.inject.add(WebSocketContext, "singleton", [self])

    def add_topic(self, name: str, cls: type[WebSocketTopic[...]]) -> None:
        self.topics[name] = _WSTypeBag(Type(cls))

    async def handle(self, request: WebSocketRequest, response: WebSocketResponse) -> None:
        try:
            content = request.json()
            if not self.is_message(content):
                raise BadRequestError(
                    "Invalid message, action must be sub, unsub, send or close",
                    "ws.bad_request",
                )
            match content["action"]:
                case "sub":
                    if not self.checker.instanceof(content, ChannelSubscribeRequest):
                        raise BadRequestError(
                            "Invalid sub action, must contain topic and channel",
                            "ws.bad_request",
                        )
                    await self._subscribe(content, response)
                case "unsub":
                    if not self.checker.instanceof(content, ChannelUnsubscribeRequest):
                        raise BadRequestError(
                            "Invalid unsub action, must contain topic and channel",
                            "ws.bad_request",
                        )
                    await self._unsubscribe(content, response)
                case "send":
                    if not self.checker.instanceof(content, ChannelSendRequest[SocketContent]):
                        raise BadRequestError(
                            "Invalid send action, must contain topic, channel and data",
                            "ws.bad_request",
                        )
                    await self._send(content, response)
                case "close":
                    await self._close(response)
        except Exception as err:
            self.logger.error(str(type(err)), str(err))
            _, content = WebErrorHandler.create_error_payload(err, self.core_section.debug)
            await response.send(json=content)

    async def remove_connection(self, response: WebSocketResponse) -> None:
        await self._close(response)

    async def _subscribe(self, request: ChannelSubscribeRequest, response: WebSocketResponse) -> None:
        topic_name = request["topic"]
        channel_name = request["channel"]
        if topic_name not in self.topics:
            raise NotFoundError("Unknown topic", "ws.topic.not_found", {"topic": topic_name})
        topic = self.topics[topic_name]
        async with self.inject.get_async_scoped_session() as subinject:
            topic_instance = subinject.instantiate(topic.t.cls)
            result = await topic_instance.subscribe(WebSocketSubscription(channel_name))
            if not result:
                raise Exception()  # TODO
            topic.add_subscription(channel_name, response)
            self._add_subscription(response, topic_name, channel_name)

    async def _unsubscribe(self, request: ChannelUnsubscribeRequest, response: WebSocketResponse) -> None:
        topic_name = request["topic"]
        channel_name = request["channel"]
        if topic_name not in self.topics:
            raise Exception()  # TODO
        topic = self.topics[topic_name]
        topic.remove_subscription(channel_name, response)
        self._remove_subscription(response, topic_name, channel_name)

    async def _send(self, request: ChannelSendRequest[SocketContent], response: WebSocketResponse) -> None:
        topic_name = request["topic"]
        if topic_name not in self.topics:
            raise NotFoundError("Unknown topic", "ws.topic.not_found", {"topic": topic_name})
        topic = self.topics[topic_name]
        if (channel := topic.match(request["channel"])) is not None:
            async with self.inject.get_async_scoped_session() as subinject:
                topic_instance = subinject.instantiate(topic.t.cls)
                message = ChannelMessage(request["channel"], request["data"], response)
                if inspect.isawaitable(res := subinject.call(channel.func, args=[topic_instance, message])):
                    await res

    async def _close(self, response: WebSocketResponse) -> None:
        if response in self.subscriptions:
            for topic_name, channels in self.subscriptions[response].items():
                for channel_name in channels:
                    self.topics[topic_name].remove_subscription(channel_name, response)
            del self.subscriptions[response]

    def _add_subscription(self, ws: WebSocketResponse, topic: str, channel: str) -> None:
        if ws not in self.subscriptions:
            self.subscriptions[ws] = {}
        resp_subs = self.subscriptions[ws]
        if topic not in resp_subs:
            resp_subs[topic] = set()
        resp_subs[topic].add(channel)

    def _remove_subscription(self, ws: WebSocketResponse, topic: str, channel: str) -> None:
        if ws not in self.subscriptions:
            raise KeyError()
        resp_subs = self.subscriptions[ws]
        if topic not in resp_subs:
            raise KeyError()
        resp_subs[topic].remove(channel)

    @staticmethod
    def is_message(content: Any) -> TypeGuard[ChannelRequest]:
        return (
            isinstance(content, dict)
            and ("action" in content)
            and (content["action"] in ("sub", "unsub", "send", "close"))
        )


class _WSTypeBag:
    def __init__(self, cls: "Type[WebSocketTopic[...]]") -> None:
        self.t = cls
        self.subs: dict[str, set[WebSocketResponse]] = {}

    def match(self, channel: str) -> WebSocketChannelMeta[Any, Any, ..., Any] | None:
        for attr in AttributeUtils.get_cls_attrs(self.t.cls).values():
            if meta.has(attr, WebSocketChannelMeta):
                chan_meta: WebSocketChannelMeta[Any, Any, ..., Any] = meta.get(attr, WebSocketChannelMeta)
                if chan_meta.pattern.match(channel):
                    return chan_meta
        return None

    def add_subscription(self, channel: str, ws: WebSocketResponse) -> None:
        if channel not in self.subs:
            self.subs[channel] = {ws}
        else:
            self.subs[channel].add(ws)

    def remove_subscription(self, channel: str, ws: WebSocketResponse) -> None:
        if channel not in self.subs:
            raise KeyError()  # TODO
        subs = self.subs[channel]
        if ws not in subs:
            raise ValueError()
        subs.remove(ws)

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
            await ws.send(json=content, encoder=lambda o: json.dumps(o, cls=JsonObjectEncoder))
