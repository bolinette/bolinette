from aiohttp import web

from bolinette.network import AccessToken
from bolinette.web import Namespace, Method
from bolinette.services import file_service

ns = Namespace('/file', file_service)

ns.defaults.get_first_by('key')


@ns.route('/{key}/download',
          method=Method.GET,
          access=AccessToken.Fresh)
async def download_file(match, **_):
    file = await file_service.get_first_by('key', match['key'])
    headers = {
        'Content-disposition': f'attachment; filename={file.name}'
    }
    return web.Response(body=file_service.file_sender(file.key),
                        headers=headers, content_type=file.mime)
