import random
import string

from bolinette.utils import paths

from bolinette import core
from bolinette.decorators import service


@service('file')
class FileService(core.Service):
    async def _generate_key(self):
        key = None
        while key is None or len(await self.get_by('key', key)):
            key = ''.join(random.choices(string.ascii_lowercase + string.digits, k=32))
        return key

    async def write_file(self, content, key):
        path = self.context.instance_path('uploads')
        if not paths.exists(path):
            paths.mkdir(path)
        with open(paths.join(path, key), 'wb') as f:
            f.write(content)

    async def delete_file(self, key):
        paths.rm(self.context.instance_path('uploads', key))

    async def delete(self, entity, **kwargs):
        ent = await super().delete(entity)
        await self.delete_file(entity.key)
        return ent

    async def save_file(self, request_file):
        params = {
            'key': await self._generate_key(),
            'name': request_file.filename,
            'mime': request_file.content_type
        }
        await self.write_file(request_file.file.read(), params['key'])
        return await self.create(params)

    async def file_sender(self, key):
        with open(self.context.instance_path('uploads', key), 'rb') as f:
            chunk = f.read(2 ** 16)
            while chunk:
                yield chunk
                chunk = f.read(2 ** 16)
