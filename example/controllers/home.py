from bolinette.blnt import Controller
from bolinette.decorators import controller, get


@controller('home', '', namespace='', use_service=False)
class HomeController(Controller):
    @get('')
    async def home_template(self):
        return self.response.render_template('index.html')
