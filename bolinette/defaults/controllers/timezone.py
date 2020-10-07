from bolinette import blnt
from bolinette.decorators import controller, get
from bolinette.defaults.services import TimezoneService


@controller('tz', '/tz')
class TimezoneController(blnt.Controller):
    @property
    def tz_service(self) -> TimezoneService:
        return self.context.service('tz')

    @get('')
    async def all_timezones(self):
        return self.response.ok('OK', await self.tz_service.get_all())
