from bolinette import transactional, response
from bolinette.marshalling import returns, expects


class Defaults:
    def __init__(self, namespace):
        self.model = namespace.model
        self.service = namespace.service
        self.route = namespace.route
    
    def get_all(self, returns_key='default'):
        @self.route('', methods=['GET'], endpoint=f'get_all_{self.model}')
        @returns(self.model, returns_key, as_list=True)
        def route():
            return response.ok('OK', self.service.get_all())
    
    def get_one(self, returns_key='default'):
        @self.route('/<id>', methods=['GET'], endpoint=f'get_one_{self.model}')
        @returns(self.model, returns_key)
        @transactional
        def route(**params):
            m_id = params.get('id')
            return response.ok('OK', self.service.get(m_id))
    
    def create(self, returns_key='default', expects_key='default'):
        @self.route('', methods=['POST'], endpoint=f'create_{self.model}')
        @returns(self.model, returns_key)
        @transactional
        @expects(self.model, expects_key)
        def route(**params):
            payload = params.get('payload')
            return response.created(f'{self.model}.created', self.service.create(payload))
    
    def update(self, returns_key='default', expects_key='default'):
        @self.route('/<id>', methods=['PUT'], endpoint=f'update_{self.model}')
        @returns(self.model, returns_key)
        @transactional
        @expects(self.model, expects_key)
        def route(**params):
            m_id = params.get('id')
            payload = params.get('payload')
            entity = self.service.get(m_id)
            return response.ok(f'{self.model}.updated', self.service.update(entity, payload))
    
    def patch(self, returns_key='default', expects_key='default'):
        @self.route('/<id>', methods=['PATCH'], endpoint=f'patch_{self.model}')
        @returns(self.model, returns_key)
        @transactional
        @expects(self.model, expects_key, patch=True)
        def route(**params):
            m_id = params.get('id')
            payload = params.get('payload')
            entity = self.service.get(m_id)
            return response.ok(f'{self.model}.updated', self.service.patch(entity, payload))
        
    def delete(self, returns_key='default'):
        @self.route('/<id>', methods=['DELETE'], endpoint=f'delete_{self.model}')
        @returns(self.model, returns_key)
        @transactional
        def route(**params):
            m_id = params.get('id')
            entity = self.service.get(m_id)
            return response.ok(f'{self.model}.deleted', self.service.delete(entity))
