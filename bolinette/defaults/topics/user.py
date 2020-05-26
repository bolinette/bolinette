from aiohttp import web as aio_web

from bolinette import blnt
from bolinette.decorators import topic, channel


@topic('user')
class UserTopic(blnt.Topic):
    @channel(r'echo')
    async def message(self, socket: aio_web.WebSocketResponse, payload, current_user, **_):
        await socket.send_str(f'{payload["message"]} from {current_user.username if current_user else "anonymous"}')
        await self.context.sockets.send_message('user', 'root', 'hey root, what\'s up?')
