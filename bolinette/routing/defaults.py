from bolinette import response


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
        def route(**params):
            pagination = None
            order_by = []
            if 'args' in params:
                if 'page' in params['args'] or 'per_page' in params['args']:
                    pagination = {
                        'page': int(params['args'].get('page', 1)),
                        'per_page': int(params['args'].get('per_page', 20)),
                        'error_out': False
                    }
                if 'order_by' in params['args']:
                    columns = params['args']['order_by'].split(',')
                    for column in columns:
                        order_args = column.split(':')
                        col_name = order_args[0]
                        order_way = order_args[1] if len(order_args) > 1 else 'asc'
                        order_by.append((col_name, order_way == 'asc'))
            return response.ok('OK', self.service.get_all(pagination, order_by))

        access_options = self._process_access_options(options)
        self.route('',
                   methods=['GET'],
                   endpoint=f'get_all_{self.model}',
                   returns=self.route.returns(self.model, returns, as_list=True),
                   **access_options)(route)

    def get_one(self, returns='default', **options):
        def route(**params):
            m_id = params.get('id')
            return response.ok('OK', self.service.get(m_id))

        access_options = self._process_access_options(options)
        self.route('/<id>',
                   methods=['GET'],
                   endpoint=f'get_one_{self.model}',
                   returns=self.route.returns(self.model, returns),
                   **access_options)(route)

    def get_first_by(self, key, returns='default', **options):
        def route(**params):
            m_id = params.get('id')
            return response.ok('OK', self.service.get_first_by(key, m_id))

        access_options = self._process_access_options(options)
        self.route('/<id>',
                   methods=['GET'],
                   endpoint=f'get_one_{self.model}',
                   returns=self.route.returns(self.model, returns),
                   **access_options)(route)

    def create(self, returns='default', expects='default', **options):
        def route(**params):
            payload = params.get('payload')
            return response.created(f'{self.model}.created', self.service.create(payload))

        access_options = self._process_access_options(options)
        self.route('',
                   methods=['POST'],
                   endpoint=f'create_{self.model}',
                   returns=self.route.returns(self.model, returns),
                   expects=self.route.expects(self.model, expects),
                   **access_options)(route)

    def update(self, returns='default', expects='default', **options):
        def route(**params):
            m_id = params.get('id')
            payload = params.get('payload')
            entity = self.service.get(m_id)
            return response.ok(f'{self.model}.updated', self.service.update(entity, payload))

        access_options = self._process_access_options(options)
        self.route('/<id>',
                   methods=['PUT'],
                   endpoint=f'update_{self.model}',
                   returns=self.route.returns(self.model, returns),
                   expects=self.route.expects(self.model, expects),
                   **access_options)(route)

    def patch(self, returns='default', expects='default', **options):
        def route(**params):
            m_id = params.get('id')
            payload = params.get('payload')
            entity = self.service.get(m_id)
            return response.ok(f'{self.model}.updated', self.service.patch(entity, payload))

        access_options = self._process_access_options(options)
        self.route('/<id>',
                   methods=['PATCH'],
                   endpoint=f'patch_{self.model}',
                   returns=self.route.returns(self.model, returns),
                   expects=self.route.expects(self.model, expects, patch=True),
                   **access_options)(route)

    def delete(self, returns='default', **options):
        def route(**params):
            m_id = params.get('id')
            entity = self.service.get(m_id)
            return response.ok(f'{self.model}.deleted', self.service.delete(entity))

        access_options = self._process_access_options(options)
        self.route('/<id>',
                   methods=['DELETE'],
                   endpoint=f'delete_{self.model}',
                   returns=self.route.returns(self.model, returns),
                   **access_options)(route)
