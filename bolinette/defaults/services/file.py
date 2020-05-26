import random
import string

from bolinette import blnt, env
from bolinette.decorators import service
from bolinette.utils import fs


@service('file')
class FileService(blnt.Service):
    async def _generate_key(self):
        key = None
        while key is None or len(await self.get_by('key', key)):
            key = ''.join(random.choices(string.ascii_lowercase + string.digits, k=32))
        return key

    async def write_file(self, content, key):
        path = env.instance_path('uploads')
        if not fs.exists(path):
            fs.mkdir(path)
        with open(fs.join(path, key), 'wb') as f:
            f.write(content)

    async def delete_file(self, key):
        fs.delete(env.instance_path('uploads', key))

    async def delete(self, entity, **_):
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
        with open(env.instance_path('uploads', key), 'rb') as f:
            chunk = f.read(2 ** 16)
            while chunk:
                yield chunk
                chunk = f.read(2 ** 16)
