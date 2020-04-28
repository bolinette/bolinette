from typing import Dict, List

import aiohttp
from aiohttp import web as aio_web

from bolinette import web, ws, env
from bolinette.exceptions import APIError
from bolinette.network import AccessToken
from bolinette.services import user_service
from bolinette.utils import console, logger


class Resources:
    def __init__(self):
        self._topics: Dict[str, ws.Topic] = {}
        self._anon_responses: List[aio_web.WebSocketResponse] = []
        self._responses: Dict[str, aio_web.WebSocketResponse] = {}

    def _register_response(self, identity: str, response: aio_web.WebSocketResponse):
        self._responses[identity] = response

    def _unregister_response(self, identity):
        del self._responses[identity]

    def _register_anon_response(self, response: aio_web.WebSocketResponse):
        self._anon_responses.append(response)

    def _unregister_anon_response(self, response: aio_web.WebSocketResponse):
        self._anon_responses.remove(response)

    def get_response(self, identity):
        return self._responses.get(identity)

    def register_topic(self, topic: 'ws.Topic'):
        self._topics[topic.name] = topic

    def __getitem__(self, key):
        return self._topics.get(key)

    async def handler(self, request):
        response = aio_web.WebSocketResponse()
        await response.prepare(request)
        logger.warning('New WS connection')

        session = None
        identity = AccessToken.Optional.check(request)
        if identity is not None:
            session = await user_service.get_by_username(identity)
        if session is not None:
            self._register_response(session.username, response)
        else:
            self._register_anon_response(response)

        async for msg in response:  # type: aiohttp.WSMessage
            try:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    payload = msg.json()
                    action = payload['action']
                    if action == 'close':
                        await response.close()
                    elif action == 'ping':
                        await response.send_str('pong')
                    else:
                        await self._topics[payload['topic']].process(response, payload, session)
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    console.print(f'ws connection closed with exception {response.exception()})')
            except APIError as e:
                for message in e.messages:
                    logger.error(message)

        if session is not None:
            self._unregister_response(session.username)
        else:
            self._unregister_anon_response(response)

        logger.warning('Closed WS connection')
        return response

    def init_app(self):
        env.topics = self
        web.resources.app.add_routes([aio_web.get('/ws', self.handler)])


resources = Resources()
