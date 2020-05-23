import asyncio

from bolinette import data
from bolinette.decorators import controller, get
from bolinette.utils import response


@controller('test', '/test')
class TestController(data.SimpleController):
    @get('/short')
    async def short_call(self, current_user, **_):
        if current_user is not None:
            await self.context.sockets.send_message('user', current_user.username, 'short call')
        return response.ok('test.short')

    @get('/long')
    async def long_call(self, current_user, **_):
        asyncio.create_task(self.detach(current_user))
        return response.ok('test.long')

    async def detach(self, current_user):
        for i in range(10):
            if current_user is not None:
                await self.context.sockets.send_message('user', current_user.username, f'long call {i}')
            await asyncio.sleep(1)
