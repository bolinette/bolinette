from bolinette import response
from bolinette.routing import Method


class Defaults:
    def __init__(self, namespace):
        self.model = namespace.model
        self.service = namespace.service
        self.route = namespace.route

    def _process_access_options(self, options):
        access_options = {}
        if 'access' in options:
            access_options['access'] = options['access']
        if 'roles' in options:
            access_options['roles'] = options['roles']
        return access_options

    def get_all(self, returns='default', **options):
        async def route(*, query, **_):
            pagination = None
            order_by = []
            if 'page' in query or 'per_page' in query:
                pagination = {
                    'page': int(query.get('page', 0)),
                    'per_page': int(query.get('per_page', 20))
                }
            if 'order_by' in query:
                columns = query['order_by'].split(',')
                for column in columns:
                    order_args = column.split(':')
                    col_name = order_args[0]
                    order_way = order_args[1] if len(order_args) > 1 else 'asc'
                    order_by.append((col_name, order_way == 'asc'))
            return response.ok('OK', await self.service.get_all(pagination, order_by))

        access_options = self._process_access_options(options)
        self.route('',
                   method=Method.GET,
                   returns=self.route.returns(self.model, returns, as_list=True),
                   **access_options)(route)

    def get_one(self, returns='default', **options):
        async def route(*, match, **_):
            return response.ok('OK', await self.service.get(match.get('id')))

        access_options = self._process_access_options(options)
        self.route('/{id}',
                   method=Method.GET,
                   returns=self.route.returns(self.model, returns),
                   **access_options)(route)

    def get_first_by(self, key, returns='default', **options):
        async def route(*, match, **_):
            return response.ok('OK', await self.service.get_first_by(key, match.get('id')))

        access_options = self._process_access_options(options)
        self.route('/{id}',
                   method=Method.GET,
                   returns=self.route.returns(self.model, returns),
                   **access_options)(route)

    def create(self, returns='default', expects='default', **options):
        async def route(*, payload, **_):
            return response.created(f'{self.model}.created', await self.service.create(payload))

        access_options = self._process_access_options(options)
        self.route('',
                   method=Method.POST,
                   returns=self.route.returns(self.model, returns),
                   expects=self.route.expects(self.model, expects),
                   **access_options)(route)

    def update(self, returns='default', expects='default', **options):
        async def route(*, match, payload, **_):
            entity = await self.service.get(match.get('id'))
            return response.ok(f'{self.model}.updated', await self.service.update(entity, payload))

        access_options = self._process_access_options(options)
        self.route('/{id}',
                   method=Method.PUT,
                   returns=self.route.returns(self.model, returns),
                   expects=self.route.expects(self.model, expects),
                   **access_options)(route)

    def patch(self, returns='default', expects='default', **options):
        async def route(*, match, payload, **_):
            entity = await self.service.get(match.get('id'))
            return response.ok(f'{self.model}.updated', await self.service.patch(entity, payload))

        access_options = self._process_access_options(options)
        self.route('/{id}',
                   method=Method.PATCH,
                   returns=self.route.returns(self.model, returns),
                   expects=self.route.expects(self.model, expects, patch=True),
                   **access_options)(route)

    def delete(self, returns='default', **options):
        async def route(*, match, **_):
            entity = await self.service.get(match.get('id'))
            return response.ok(f'{self.model}.deleted', await self.service.delete(entity))

        access_options = self._process_access_options(options)
        self.route('/{id}',
                   method=Method.DELETE,
                   returns=self.route.returns(self.model, returns),
                   **access_options)(route)
