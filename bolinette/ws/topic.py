from typing import Pattern, List, Any, Dict
import re

from aiohttp.web_ws import WebSocketResponse

from bolinette import ws
from bolinette.network import transaction


class Channel:
    def __init__(self, name: str, rule: Pattern[str], function):
        self.name = name
        self.rule = re.compile(f'^{rule}$')
        self.function = function


class Topic:
    def __init__(self, name: str, *, login_required=False, roles=None):
        self.name = name
        self.login_required = login_required
        self.roles = roles or []
        self._channels = []
        self._subscription_func = self._default_subscription_func
        self._subscriptions: Dict[str, List[WebSocketResponse]] = {}
        ws.resources.register_topic(self)

    @property
    def subscriptions(self):
        return self._subscriptions

    @staticmethod
    def _default_subscription_func(topic, response: WebSocketResponse, *, payload: Dict[str, Any], **_):
        channel_name = payload['channel']
        if channel_name not in topic.subscriptions:
            topic.subscriptions[channel_name] = []
        topic.subscriptions[channel_name].append(response)

    async def _receive_message(self, payload: Dict[str, Any], current_user):
        for channel in self._channels:
            if channel.rule.match(payload['channel']):
                await channel.function(self, payload=payload, current_user=current_user)

    async def _receive_subscription(self, response: WebSocketResponse, payload: Dict[str, Any], current_user):
        self._subscription_func(self, response, payload=payload, current_user=current_user)

    async def send_message(self, channels: List[str], message: Any):
        for channel in channels:
            if any(filter(lambda r: r.closed, self._subscriptions[channel])):
                self._subscriptions[channel] = list(filter(lambda r: not r.closed, self._subscriptions[channel]))
            for response in self._subscriptions[channel]:
                await response.send_json({
                    'topic': self.name,
                    'channel': channel,
                    'message': message
                })

    async def process(self, response: WebSocketResponse, payload, current_user):
        if self.login_required and current_user is None:
            return
        action = payload['action']
        with transaction:
            if action == 'send':
                await self._receive_message(payload, current_user)
            elif action == 'subscribe':
                await self._receive_subscription(response, payload, current_user)

    def subscribe(self, function):
        self._subscription_func = function
        return function

    def channel(self, rule: Pattern[str]):
        def decorator(function):
            self._channels.append(Channel(function.__name__, rule, function))
            return function

        return decorator
