from bolinette import web
from bolinette.decorators import controller, get


@controller('home', '', namespace='', use_service=False)
class HomeController(web.Controller):
    @get('')
    async def home_template(self):
        """
        Renders and returns the index.html jinja template
        """
        return self.response.render_template('index.html')

    @get('/hello')
    @get('/hello/{name}')
    async def hello(self, match):
        """
        Says hello to you

        -response 200 returns: Hello with your name
        """
        if 'name' in match:
            name = match['name']
        else:
            name = 'user'
        return self.response.ok(data=f'Hello {name}!')
