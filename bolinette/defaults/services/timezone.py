import pytz

from bolinette import core
from bolinette.decorators import service


@service('tz')
class TimezoneService(core.SimpleService):
    async def get_all(self):
        return [tz for tz in pytz.all_timezones]

    async def is_valid(self, key):
        return key in pytz.all_timezones
