from aiohttp import web as aio_web

from bolinette.core import BolinetteContext
from bolinette.data.defaults.services import FileService
from bolinette.web import ext, WebContext, Controller


@ext.controller("file", "/file", middlewares=["auth"])
class FileController(Controller):
    def __init__(
        self, context: BolinetteContext, web_ctx: WebContext, file_service: FileService
    ):
        super().__init__(context, web_ctx)
        self.file_service = file_service

    def default_routes(self):
        return [self.defaults.get_one(key="key")]

    @ext.route.get("/{key}/download")
    async def download_file(self, match):
        file = await self.service.get_first_by("key", match["key"])
        headers = {"Content-disposition": f"attachment; filename={file.name}"}
        return aio_web.Response(
            body=self.file_service.file_sender(file.key),
            headers=headers,
            content_type=file.mime,
        )
