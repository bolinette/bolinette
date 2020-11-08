import re
from typing import Dict, List

from aiohttp import web as aio_web

from bolinette import core


class Topic:
    __blnt__: 'TopicMetadata' = None

    def __init__(self, context: 'core.BolinetteContext'):
        self.context = context
        self.__props__ = TopicProps(self)
        self._subscriptions: Dict[str, List[aio_web.WebSocketResponse]] = {}

    async def receive_subscription(self, channel: str, resp: aio_web.WebSocketResponse):
        if channel not in self._subscriptions:
            self._subscriptions[channel] = []
        self._subscriptions[channel].append(resp)

    def _remove_closed_connections(self, channel: str):
        subs = self._subscriptions.get(channel)
        if subs is None:
            return
        self._subscriptions[channel] = list(filter(lambda c: not c.closed, subs))
        return self._subscriptions[channel]

    def subscriptions(self, channel: str) -> List[aio_web.WebSocketResponse]:
        return self._remove_closed_connections(channel) or []

    def __repr__(self):
        return f'<Topic {self.__blnt__.name}>'


class TopicMetadata:
    def __init__(self, name):
        self.name = name


class TopicProps:
    def __init__(self, topic: Topic):
        self.topic = topic

    def _get_attribute_of_type(self, attr_type):
        return dict([(name, attribute)
                     for name, attribute in vars(self.topic.__class__).items()
                     if isinstance(attribute, attr_type)])

    def get_channels(self) -> Dict[str, 'TopicChannel']:
        return self._get_attribute_of_type(TopicChannel)


class TopicChannel:
    def __init__(self, function, rule):
        self.function = function
        self.rule = rule
        self.re = re.compile(f'^{rule}$')

    def __repr__(self):
        return f'<Channel {self.rule}>'
