import re
from collections.abc import Iterator

from aiohttp import web as aio_web

from bolinette import abc, blnt
from bolinette.blnt import Properties


class Topic(abc.WithContext):
    __blnt__: 'TopicMetadata' = None

    def __init__(self, context: 'blnt.BolinetteContext'):
        super().__init__(context)
        self.__props__ = TopicProps(self)
        self._subscriptions: dict[str, list[aio_web.WebSocketResponse]] = {}

    async def receive_subscription(self, channel: str, resp: aio_web.WebSocketResponse):
        if channel not in self._subscriptions:
            self._subscriptions[channel] = []
        self._subscriptions[channel].append(resp)

    async def validate_subscription(self, *args, **kwargs) -> bool:
        return True

    def _remove_closed_connections(self, channel: str) -> list[aio_web.WebSocketResponse]:
        subs = self._subscriptions.get(channel)
        if subs is None:
            return []
        self._subscriptions[channel] = list(filter(lambda c: not c.closed, subs))
        return self._subscriptions[channel]

    def subscriptions(self, channel: str) -> list[aio_web.WebSocketResponse]:
        return self._remove_closed_connections(channel)

    @staticmethod
    async def send(socket: aio_web.WebSocketResponse, data):
        await socket.send_json({'data': data})

    @staticmethod
    async def send_error(socket: aio_web.WebSocketResponse, error: str):
        await socket.send_json({'error': error})

    def __repr__(self):
        return f'<Topic {self.__blnt__.name}>'


class TopicMetadata:
    def __init__(self, name):
        self.name = name


class TopicProps(Properties):
    def __init__(self, topic: Topic):
        super().__init__(topic)

    def get_channels(self) -> Iterator[tuple[str, 'TopicChannel']]:
        return self._get_cls_attributes_of_type(type(self.parent), TopicChannel)


class TopicChannel:
    def __init__(self, function, rule):
        self.function = function
        self.rule = rule
        self.re = re.compile(f'^{rule}$')

    def __repr__(self):
        return f'<Channel {self.rule}>'
