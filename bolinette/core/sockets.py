import asyncio
from typing import Dict, List, Union

import aiohttp
from aiohttp import web as aio_web
from aiohttp.web_request import Request
from bolinette.utils import logger

from bolinette import core, types, blnt
from bolinette.exceptions import APIError


class BolinetteSockets:
    def __init__(self, context: 'core.BolinetteContext'):
        self.context = context
        self._topics: Dict[str, 'blnt.Topic'] = {}
        self._channels: Dict[str, List['blnt.TopicChannel']] = {}
        self._socket_sessions: Dict[str, aio_web.WebSocketResponse] = {}
        self._anon_socket_sessions: List[aio_web.WebSocketResponse] = []

    def add_topic(self, name: str, topic: 'blnt.Topic'):
        self._topics[name] = topic

    def topic(self, name: str) -> 'blnt.Topic':
        return self._topics.get(name)

    def add_channel(self, topic: str, channel: 'blnt.TopicChannel'):
        if topic not in self._channels:
            self._channels[topic] = []
        self._channels[topic].append(channel)

    def channels(self, topic: str) -> List['blnt.TopicChannel']:
        return self._channels.get(topic) or []
    
    async def send_message(self, topic: str, channels: Union[str, List[str]], message):
        socket_topic = self.topic(topic)
        if socket_topic is None:
            return
        if not isinstance(channels, list):
            channels = [channels]
        pending_tasks = []
        for channel in channels:
            subscriptions = socket_topic.subscriptions(channel)
            if subscriptions is not None:
                for subscription in subscriptions:
                    if subscription.closed:
                        continue
                    pending_tasks.append(subscription.send_json({
                       'topic': topic,
                       'channel': channel,
                       'message': message
                    }))
        await asyncio.gather(*pending_tasks)

    def add_socket_session(self, username: str, session: aio_web.WebSocketResponse):
        self._socket_sessions[username] = session

    def delete_socket_session(self, username: str):
        del self._socket_sessions[username]

    def add_anon_socket_session(self, session: aio_web.WebSocketResponse):
        self._anon_socket_sessions.append(session)

    def delete_anon_socket_session(self, session: aio_web.WebSocketResponse):
        self._anon_socket_sessions.remove(session)

    def init_socket_handler(self):
        self.context.app.add_routes([aio_web.get('/ws', SocketHandler().__call__)])


class SocketHandler:
    def __init__(self):
        pass

    async def __call__(self, request: Request):
        context: core.BolinetteContext = request.app['blnt']
        user_service = context.service('user')
        socket = aio_web.WebSocketResponse()
        await socket.prepare(request)
        logger.warning('New WS connection')

        current_user = None
        identity = types.web.AccessToken.Optional.check(context, request)
        if identity is not None:
            current_user = await user_service.get_by_username(identity)
        if current_user is not None:
            context.sockets.add_socket_session(current_user.username, socket)
        else:
            context.sockets.add_anon_socket_session(socket)

        async for msg in socket:  # type: aiohttp.WSMessage
            try:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    payload = msg.json()
                    action = payload['action']
                    if action == 'close':
                        await socket.close()
                    elif action == 'ping':
                        await socket.send_str('pong')
                    else:
                        await self.process_topic_message(context, socket, payload, current_user)
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.warning(f'ws connection closed with exception {socket.exception()})')
            except APIError as e:
                logger.error(e.message)

        if current_user is not None:
            context.sockets.delete_socket_session(current_user.username)
        else:
            context.sockets.delete_anon_socket_session(socket)

        logger.warning('Closed WS connection')
        return socket

    async def process_topic_message(self, context: 'core.BolinetteContext',
                                    socket: aio_web.WebSocketResponse, payload, current_user):
        action = payload['action']
        topic = context.sockets.topic(payload['topic'])
        if topic is not None:
            with core.Transaction(context):
                if action == 'subscribe':
                    await topic.receive_subscription(payload['channel'], socket)
                elif action == 'send':
                    channels = context.sockets.channels(payload['topic'])
                    for channel in channels:
                        if channel.re.match(payload['channel']):
                            await channel.function(topic, socket=socket, payload=payload, current_user=current_user)
