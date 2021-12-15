import pytz

from bolinette import data
from bolinette.decorators import service


@service('tz')
class TimezoneService(data.SimpleService):
    @staticmethod
    async def get_all():
        return [tz for tz in pytz.all_timezones]

    @staticmethod
    async def is_valid(key):
        return key in pytz.all_timezones
