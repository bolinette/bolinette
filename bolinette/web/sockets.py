import asyncio
from json import JSONDecodeError

import aiohttp
from aiohttp import web as aio_web
from aiohttp.web_request import Request

from bolinette import abc, blnt, web
from bolinette.exceptions import APIError
from bolinette.utils.functions import async_invoke


class BolinetteSockets(abc.WithContext):
    def __init__(self, context: 'blnt.BolinetteContext'):
        super().__init__(context)
        self._topics: dict[str, 'web.Topic'] = {}
        self._channels: dict[str, list['web.TopicChannel']] = {}
        self._socket_sessions: dict[str, aio_web.WebSocketResponse] = {}
        self._anon_socket_sessions: list[aio_web.WebSocketResponse] = []

    def add_topic(self, name: str, topic: 'web.Topic'):
        self._topics[name] = topic

    def topic(self, name: str) -> 'web.Topic':
        return self._topics.get(name)

    def add_channel(self, topic: str, channel: 'web.TopicChannel'):
        if topic not in self._channels:
            self._channels[topic] = []
        self._channels[topic].append(channel)

    def channels(self, topic: str) -> list['web.TopicChannel']:
        return self._channels.get(topic) or []

    async def send_message(self, topic: str, channels: str | list[str], message):
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
        context: blnt.BolinetteContext = request.app['blnt']
        user_service = context.inject.require('service', 'user', immediate=True)
        socket = aio_web.WebSocketResponse()
        await socket.prepare(request)

        current_user = None
        identity = context.jwt.verify(request, optional=True, fresh=True)
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
                    context.logger.warning(f'ws connection closed with exception {socket.exception()})')
            except APIError as e:
                context.logger.error(e.message)
            except JSONDecodeError:
                context.logger.error('sockets.non_deserializable_payload')

        if current_user is not None:
            context.sockets.delete_socket_session(current_user.username)
        else:
            context.sockets.delete_anon_socket_session(socket)
        return socket

    @staticmethod
    async def _subscribe(topic: web.Topic, socket: aio_web.WebSocketResponse, payload, current_user):
        if await async_invoke(topic.validate_subscription, payload=payload, socket=socket, current_user=current_user):
            await topic.receive_subscription(payload['channel'], socket)

    async def process_topic_message(self, context: 'blnt.BolinetteContext',
                                    socket: aio_web.WebSocketResponse, payload, current_user):
        action = payload['action']
        topic = context.sockets.topic(payload['topic'])
        if topic is not None:
            async with blnt.Transaction(context):
                if action == 'subscribe':
                    await self._subscribe(topic, socket, payload, current_user)
                elif action == 'send':
                    channels = context.sockets.channels(payload['topic'])
                    for channel in channels:
                        if channel.re.match(payload['channel']):
                            await async_invoke(channel.function, topic, socket=socket, payload=payload,
                                               current_user=current_user)
