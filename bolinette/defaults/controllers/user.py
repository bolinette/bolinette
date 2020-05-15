from bolinette import data
from bolinette.decorators import controller, get
from bolinette.utils.response import response


@controller('user', '/user')
class UserController(data.Controller):
    @get('/test')
    async def test_route(self, **_):
        user = await self.service.get(1)
        return response.ok('OK', {'username': user.username})
