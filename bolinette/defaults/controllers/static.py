import mimetypes

from aiohttp import web as aio_web
from bolinette.utils import paths

from bolinette import web
from bolinette.decorators import get, controller


@controller('static', namespace='', use_service=False)
class StaticController(web.Controller):
    @staticmethod
    async def _file_sender(path):
        with open(path, 'rb') as file:
            chunk = file.read(2 ** 16)
            while chunk:
                yield chunk
                chunk = file.read(2 ** 16)

    @get('/{route:.*}')
    async def get_static_file(self, match):
        """
        Gets a static file from its path relative to the app static folder
        """
        route = match['route'].split('/')
        if route == ['']:
            route = ['index.html']
        path = self.context.static_path(*route)
        if paths.exists(path):
            content_type = mimetypes.guess_type(path)[0]
            return aio_web.Response(body=self._file_sender(path),
                                    status=200, content_type=content_type or 'text/plain')
        return aio_web.Response(body='global.404_error', status=404, content_type='text/plain')
