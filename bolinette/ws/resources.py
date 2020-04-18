import aiohttp
from aiohttp import web as aio_web

from bolinette import web, ws
from bolinette.utils import console


class Resources:
    def __init__(self):
        self.topics = {}

    def register_topic(self, topic: 'ws.Topic'):
        self.topics[topic.name] = topic

    async def socket_handler(self, request):
        socket = aio_web.WebSocketResponse()
        await socket.prepare(request)

        async for msg in socket:  # type: aiohttp.WSMessage
            if msg.type == aiohttp.WSMsgType.TEXT:
                payload = msg.json()
                action = payload['action']
                if action == 'close':
                    await socket.close()
                    break
                topic = self.topics[payload['topic']]
                if action == 'send':
                    await topic.receive_message(payload['channel'], payload['message'])
                elif action == 'subscribe':
                    await topic.receive_subscription(payload['channel'], socket)
            elif msg.type == aiohttp.WSMsgType.ERROR:
                console.print(f'ws connection closed with exception {socket.exception()})')
        return socket

    def init_app(self):
        web.resources.app.add_routes([aio_web.get('/ws', self.socket_handler)])


resources = Resources()
