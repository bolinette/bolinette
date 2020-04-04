from bolinette import response
from bolinette.routing import Namespace, Method
from bolinette.services import timezone_service

ns = Namespace('/tz', timezone_service)


@ns.route('', method=Method.GET)
async def all_timezones(**_):
    return response.ok('OK', await timezone_service.get_all())
