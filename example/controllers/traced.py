from bolinette.web import Controller, controller, route


@controller('traced', use_service=False, middlewares=['auth'])
class TracedController(Controller):
    @route.get('', middlewares=['tracking|name=get_hello'])
    async def get_hello(self):
        return 'Hello!'
