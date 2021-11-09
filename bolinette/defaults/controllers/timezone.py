from bolinette import abc, web
from bolinette.decorators import controller, get
from bolinette.defaults.services import TimezoneService


@controller('tz', '/tz')
class TimezoneController(web.Controller):
    def __init__(self, context: abc.Context, tz_service: TimezoneService):
        super().__init__(context)
        self.tz_service = tz_service

    @get('')
    async def all_timezones(self):
        """
        Gets all available IANA timezones
        """
        return self.response.ok(data=await self.tz_service.get_all())
