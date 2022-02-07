from aiohttp import web as aio_web

from bolinette.web import ext, Topic


@ext.topic("role")
class RoleTopic(Topic):
    async def validate_subscription(
        self, socket: aio_web.WebSocketResponse, payload, current_user
    ) -> bool:
        if current_user is None:
            await self.send_error(socket, f'role.{payload["channel"]}.require_auth')
            return False
        if current_user.username != payload["channel"]:
            await self.send_error(socket, f'role.{payload["channel"]}.forbidden')
            return False
        return True
