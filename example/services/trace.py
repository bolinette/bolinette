from bolinette import core
from bolinette.decorators import service


@service('trace')
class TraceService(core.Service):
    async def inc_trace(self, page_name, user, timestamp):
        trace = await self.repo.query().filter_by(name=page_name, user_id=user.id).first()
        if trace is None:
            await self.repo.create({'name': page_name, 'visits': 1, 'last_visit': timestamp, 'user': user})
        else:
            trace.visits += 1
            trace.last_visit = timestamp
