from bolinette import web, blnt
from bolinette.decorators import controller, get, injected
from bolinette.defaults.services import TimezoneService


@controller('tz', '/tz')
class TimezoneController(web.Controller):
    @injected
    def tz_service(self, inject: 'blnt.BolinetteInjection') -> TimezoneService:
        return inject.services.require('tz')

    @get('')
    async def all_timezones(self):
        """
        Gets all available IANA timezones
        """
        return self.response.ok(data=await self.tz_service.get_all())
