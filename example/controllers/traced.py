from bolinette import web
from bolinette.decorators import controller, get


@controller('traced', use_service=False, middlewares=['auth'])
class TracedController(web.Controller):
    @get('', middlewares=['tracking|name=get_hello'])
    async def get_hello(self):
        return 'Hello!'
