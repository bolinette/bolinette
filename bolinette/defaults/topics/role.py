from aiohttp import web as aio_web

from bolinette import web
from bolinette.decorators import topic


@topic('role')
class RoleTopic(web.Topic):
    async def validate_subscription(self, socket: aio_web.WebSocketResponse, payload, current_user) -> bool:
        if current_user is None:
            await self.send_error(socket, f'role.{payload["channel"]}.require_auth')
            return False
        if current_user.username != payload['channel']:
            await self.send_error(socket, f'role.{payload["channel"]}.forbidden')
            return False
        return True
