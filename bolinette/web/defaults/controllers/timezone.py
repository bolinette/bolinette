from bolinette.core import BolinetteContext
from bolinette.web import ext, WebContext, Controller
from bolinette.data.defaults.services import TimezoneService


@ext.controller("tz", "/tz")
class TimezoneController(Controller):
    def __init__(
        self,
        context: BolinetteContext,
        web_ctx: WebContext,
        tz_service: TimezoneService,
    ):
        super().__init__(context, web_ctx)
        self.tz_service = tz_service

    @ext.route.get("")
    async def all_timezones(self):
        """
        Gets all available IANA timezones
        """
        return self.response.ok(data=await self.tz_service.get_all())
