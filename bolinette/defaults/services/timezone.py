import pytz

from bolinette import core
from bolinette.decorators import service


@service('tz')
class TimezoneService(core.SimpleService):
    @staticmethod
    async def get_all():
        return [tz for tz in pytz.all_timezones]

    @staticmethod
    async def is_valid(key):
        return key in pytz.all_timezones
