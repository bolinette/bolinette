from aiohttp import web as aio_web

from bolinette import blnt, types
from bolinette.decorators import controller, get
from bolinette.defaults.services import FileService


@controller('file', '/file')
class FileController(blnt.Controller):
    @property
    def file_service(self) -> FileService:
        return self.context.service('file')

    def default_routes(self):
        return [
            self.defaults.get_one(key='key')
        ]

    @get('/{key}/download',
         access=types.web.AccessToken.Fresh)
    async def download_file(self, match, **_):
        file = await self.service.get_first_by('key', match['key'])
        headers = {
            'Content-disposition': f'attachment; filename={file.name}'
        }
        return aio_web.Response(body=self.file_service.file_sender(file.key),
                                headers=headers, content_type=file.mime)
