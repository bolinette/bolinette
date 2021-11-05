from bolinette import abc, web
from bolinette.decorators import controller, get, injected
from bolinette.defaults.services import TimezoneService


@controller('tz', '/tz')
class TimezoneController(web.Controller):
    @injected
    def tz_service(self, inject: abc.inject.Injection):
        return inject.require(TimezoneService)

    @get('')
    async def all_timezones(self):
        """
        Gets all available IANA timezones
        """
        return self.response.ok(data=await self.tz_service.get_all())
