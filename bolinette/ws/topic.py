from typing import Pattern, List, Any, Dict
import re

from aiohttp.web_ws import WebSocketResponse

from bolinette import ws


class Channel:
    def __init__(self, name: str, rule: Pattern[str], function):
        self.name = name
        self.rule = re.compile(f'^{rule}$')
        self.function = function


class Topic:
    def __init__(self, name: str):
        self.name = name
        self._channels = []
        self._subscription_func = self._default_subscription_func
        self._subscriptions: Dict[str, List[WebSocketResponse]] = {}
        ws.resources.register_topic(self)

    def _default_subscription_func(self, channel_name: str, session):
        if channel_name not in self._subscriptions:
            self._subscriptions[channel_name] = []
        self._subscriptions[channel_name].append(session)

    async def receive_message(self, channel_name: str, message):
        for channel in self._channels:
            if channel.rule.match(channel_name):
                await channel.function(channel=channel_name, message=message)

    async def send_message(self, channels: List[str], message: Dict[str, Any]):
        for channel in channels:
            if any(filter(lambda s: s.closed, self._subscriptions[channel])):
                self._subscriptions[channel] = list(filter(lambda s: not s.closed, self._subscriptions[channel]))
            for session in self._subscriptions[channel]:
                await session.send_json(message)

    async def receive_subscription(self, channel_name: str, session):
        self._subscription_func(channel_name, session)

    def subscribe(self, function):
        self._subscription_func = function
        return function

    def channel(self, rule: Pattern[str]):
        def decorator(function):
            self._channels.append(Channel(function.__name__, rule, function))
            return function

        return decorator
