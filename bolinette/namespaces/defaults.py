from bolinette import response


class Defaults:
    def __init__(self, namespace):
        self.model = namespace.model
        self.service = namespace.service
        self.route = namespace.route

    def get_all(self, returns='default'):
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

        self.route('', methods=['GET'], endpoint=f'get_all_{self.model}',
                   returns={'model': self.model, 'key': returns, 'as_list': True})(route)

    def get_one(self, returns='default'):
        def route(**params):
            m_id = params.get('id')
            return response.ok('OK', self.service.get(m_id))

        self.route('/<id>', methods=['GET'], endpoint=f'get_one_{self.model}',
                   returns={'model': self.model, 'key': returns})(route)

    def create(self, returns='default', expects='default'):
        def route(**params):
            payload = params.get('payload')
            return response.created(f'{self.model}.created', self.service.create(payload))

        self.route('', methods=['POST'], endpoint=f'create_{self.model}',
                   returns={'model': self.model, 'key': returns},
                   expects={'model': self.model, 'key': expects})(route)

    def update(self, returns='default', expects='default'):
        def route(**params):
            m_id = params.get('id')
            payload = params.get('payload')
            entity = self.service.get(m_id)
            return response.ok(f'{self.model}.updated', self.service.update(entity, payload))

        self.route('/<id>', methods=['PUT'], endpoint=f'update_{self.model}',
                   returns={'model': self.model, 'key': returns},
                   expects={'model': self.model, 'key': expects})(route)

    def patch(self, returns='default', expects='default'):
        def route(**params):
            m_id = params.get('id')
            payload = params.get('payload')
            entity = self.service.get(m_id)
            return response.ok(f'{self.model}.updated', self.service.patch(entity, payload))

        self.route('/<id>', methods=['PATCH'], endpoint=f'patch_{self.model}',
                   returns={'model': self.model, 'key': returns},
                   expects={'model': self.model, 'key': expects, 'patch': True})(route)

    def delete(self, returns='default'):
        def route(**params):
            m_id = params.get('id')
            entity = self.service.get(m_id)
            return response.ok(f'{self.model}.deleted', self.service.delete(entity))

        self.route('/<id>', methods=['DELETE'], endpoint=f'delete_{self.model}',
                   returns={'model': self.model, 'key': returns})(route)
