from aiohttp import web as aio_web

from bolinette import web, blnt
from bolinette.decorators import controller, get, injected
from bolinette.defaults.services import FileService


@controller('file', '/file', middlewares=['auth'])
class FileController(web.Controller):
    @injected
    def file_service(self, inject: 'blnt.BolinetteInjection') -> FileService:
        return inject.services.require('file')

    def default_routes(self):
        return [
            self.defaults.get_one(key='key')
        ]

    @get('/{key}/download')
    async def download_file(self, match):
        file = await self.service.get_first_by('key', match['key'])
        headers = {
            'Content-disposition': f'attachment; filename={file.name}'
        }
        return aio_web.Response(body=self.file_service.file_sender(file.key),
                                headers=headers, content_type=file.mime)
