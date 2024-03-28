import inspect
import json
from typing import Any, TypeGuard

from aiohttp.web import Request, Response, StreamResponse, WebSocketResponse, WSMsgType

from bolinette.core import Cache, Logger, meta
from bolinette.core.injection import Injection, init_method
from bolinette.core.mapping.json import JsonObjectEncoder
from bolinette.core.types import Type, TypeChecker
from bolinette.core.utils import AttributeUtils
from bolinette.web.ws import WebSocketMessage, WebSocketSubscription, WebSocketTopic
from bolinette.web.ws.channel import WebSocketChannelMeta
from bolinette.web.ws.requests import (
    SocketContent,
    WebSocketCloseRequest,
    WebSocketRequest,
    WebSocketSendRequest,
    WebSocketSubscribeRequest,
    WebSocketUnsubscribeRequest,
)
from bolinette.web.ws.topic import WebSocketTopicMeta


class WebSocketHandler:
    def __init__(self, logger: "Logger[WebSocketHandler]", checker: TypeChecker, inject: Injection) -> None:
        self.logger = logger
        self.checker = checker
        self.topics: dict[str, _WSTypeBag]
        self.inject = inject
        self.subscriptions: dict[WebSocketResponse, dict[str, set[str]]] = {}

    @init_method
    def _init_topics(self, cache: Cache) -> None:
        topics: dict[str, _WSTypeBag] = {}
        for cls in cache.get(WebSocketTopic, hint=type[WebSocketTopic[...]], raises=False):
            topic_meta = meta.get(cls, WebSocketTopicMeta)
            topics[topic_meta.name] = _WSTypeBag(Type(cls))
        self.topics = topics

    async def handle(self, request: Request) -> Response | StreamResponse:
        ws = WebSocketResponse()
        await ws.prepare(request)
        self.logger.info(f"Accepted websocket connection #{hash(ws)}")
        async for msg in ws:
            match msg.type:
                case WSMsgType.CONTINUATION:
                    raise NotImplementedError()
                case WSMsgType.TEXT | WSMsgType.text:
                    content = msg.json()
                    if not self.is_message(content):
                        raise Exception()  # TODO
                    match content["action"]:
                        case "sub":
                            if not self.checker.instanceof(content, WebSocketSubscribeRequest):
                                raise Exception()  # TODO
                            await self._subscribe(content, ws)
                        case "unsub":
                            if not self.checker.instanceof(content, WebSocketUnsubscribeRequest):
                                raise Exception()  # TODO
                            await self._unsubscribe(content, ws)
                        case "send":
                            if not self.checker.instanceof(content, WebSocketSendRequest[SocketContent]):
                                raise Exception()  # TODO
                            await self._send(content, ws)
                        case "close":
                            if not self.checker.instanceof(content, WebSocketCloseRequest):
                                raise Exception()  # TODO
                            await self._close(ws)
                case WSMsgType.BINARY | WSMsgType.binary:
                    raise NotImplementedError()
                case WSMsgType.PING | WSMsgType.ping:
                    await ws.pong(msg.data)
                case WSMsgType.PONG | WSMsgType.pong:
                    pass
                case WSMsgType.CLOSE | WSMsgType.close:
                    raise NotImplementedError()
                case WSMsgType.CLOSING | WSMsgType.closing:
                    raise NotImplementedError()
                case WSMsgType.CLOSED | WSMsgType.closed:
                    raise NotImplementedError()
                case WSMsgType.ERROR | WSMsgType.error:
                    raise NotImplementedError()
        await self._close(ws)
        self.logger.info(f"Closed websocket connection #{hash(ws)}")
        return ws

    async def _subscribe(self, request: WebSocketSubscribeRequest, ws: WebSocketResponse) -> None:
        topic_name = request["topic"]
        channel_name = request["channel"]
        if topic_name not in self.topics:
            raise Exception()  # TODO
        topic = self.topics[topic_name]
        async with self.inject.get_async_scoped_session() as subinject:
            subinject.add(WebSocketContext, "scoped", [self])
            topic_instance = subinject.instantiate(topic.t.cls)
            result = await topic_instance.subscribe(WebSocketSubscription(channel_name))
            if not result:
                raise Exception()  # TODO
            topic.add_subscription(channel_name, ws)
            self._add_subscription(ws, topic_name, channel_name)

    async def _unsubscribe(self, request: WebSocketUnsubscribeRequest, ws: WebSocketResponse) -> None:
        topic_name = request["topic"]
        channel_name = request["channel"]
        if topic_name not in self.topics:
            raise Exception()  # TODO
        topic = self.topics[topic_name]
        topic.remove_subscription(channel_name, ws)
        self._remove_subscription(ws, topic_name, channel_name)

    async def _send(self, request: WebSocketSendRequest[SocketContent], ws: WebSocketResponse) -> None:
        if request["topic"] not in self.topics:
            raise Exception()  # TODO
        topic = self.topics[request["topic"]]
        if (channel := topic.match(request["channel"])) is not None:
            async with self.inject.get_async_scoped_session() as subinject:
                subinject.add(WebSocketContext, "scoped", [self])
                topic_instance = subinject.instantiate(topic.t.cls)
                message = WebSocketMessage(request["channel"], request["data"], ws)
                if inspect.isawaitable(res := subinject.call(channel.func, args=[topic_instance, message])):
                    await res

    async def _close(self, ws: WebSocketResponse) -> None:
        await ws.close()
        if ws in self.subscriptions:
            for topic_name, channels in self.subscriptions[ws].items():
                for channel_name in channels:
                    self.topics[topic_name].remove_subscription(channel_name, ws)

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
    def is_message(content: Any) -> TypeGuard[WebSocketRequest]:
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
            await ws.send_json(content, dumps=lambda o: json.dumps(o, cls=JsonObjectEncoder))
