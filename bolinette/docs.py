import re
from typing import Any, Literal

import yaml
from aiohttp_swagger import setup_swagger

from bolinette import abc, blnt, web, types, mapping
from bolinette.decorators import get
from bolinette.utils import paths, files


class Documentation(abc.WithContext):
    def __init__(self, context: 'blnt.BolinetteContext'):
        super().__init__(context)
        self.swagger_path = self.context.instance_path('swagger.yaml')
        self._path_param_regex = re.compile(r'{([^}]*)}')
        self._response_regex = re.compile(r'^-response ([\d]{3})(?: ([^:]*))?(?:: ?(.*))?$')
        self._response_type_regex = re.compile(r'file\[([^]]*)]')
        self._response_returns_regex = re.compile(r'returns')
        self._type_map = {
            types.db.Integer: {'type': 'integer'},
            types.db.Boolean: {'type': 'boolean'},
            types.db.String: {'type': 'string'},
            types.db.Email: {'type': 'string', 'format': 'email'},
            types.db.Float: {'type': 'number', 'format': 'float'},
            types.db.Date: {'type': 'string', 'format': 'date-time'},
            types.db.Password: {'type': 'string', 'format': 'password'}
        }

    def build(self):
        self.context.logger.info('Building API documentation')
        content = {
            'openapi': '3.0.0',
            'info': {
                'title': self.context.manifest.get('name', 'Bolinette App'),
                'description': self.context.manifest.get('desc', 'My web app built with the Bolinette framework'),
                'version': self.context.manifest.get('version', '0.0.1')
            },
            'servers': [{'url': f'http://localhost:{self.context.env.get("port", 5000)}'}],
            'paths': self._build_routes(),
            'components': {
                'schemas': self._build_schemas()
            }
        }
        files.write(self.swagger_path, yaml.safe_dump(content))

    def _build_routes(self):
        routes = {}
        for path, method, route in self.context.resources.routes:
            self._build_route(path, method, route, routes)
        return routes

    def _build_route(self, path: str, method: web.HttpMethod, route: web.ControllerRoute, routes: dict[str, Any]):
        if route.controller is not None:
            if not path:
                path = '/'
            if path not in routes:
                routes[path] = {}
            docs = {
                'tags': [f'{route.controller.__blnt__.name} controller']
            }
            parsed_docs = self._parse_docs(route.docstring, route)
            if len(parsed_docs) > 0:
                docs.update(parsed_docs)
            if ('responses' not in docs or len(docs['responses']) <= 0) and route.returns:
                if 'responses' not in docs:
                    docs['responses'] = {}
                ref = self._build_ref(route, 'response')
                if len(ref) > 0:
                    docs['responses'][200] = {'content': {'application/json': {'schema': ref}}}
            parameters = self._parse_path(path)
            if len(parameters) > 0:
                docs['parameters'] = parameters
            routes[path][method.name.lower()] = docs
        if route.inner_route is not None:
            self._build_route(path, method, route.inner_route, routes)

    def _parse_docs(self, docstring: str | None, route: web.ControllerRoute):
        if not docstring:
            return {}
        docs = {}
        parsed = [s.strip('\n ') for s in docstring.split('\n\n')]
        doc_index = 0
        for part in parsed:
            self._parse_doc_line(part, docs, doc_index, route)
            doc_index += 1
        return docs

    def _parse_doc_line(self, part: str, docs: dict[str, Any], index: int, route: web.ControllerRoute):
        if index == 0:
            docs['summary'] = part
            return
        if part.startswith('-'):
            lines = [line.strip() for line in part.split('\n')]
            commands = []
            for line in lines:
                if line.startswith('-'):
                    commands.append(line)
                else:
                    commands[-1] += f' {line}'
            for command in commands:
                if command.startswith('-response'):
                    self._parse_responses(command, docs, route)
            return
        if 'description' not in docs:
            docs['description'] = ''
        if len(docs['description']) > 0:
            docs['description'] += '\n\n'
        docs['description'] += part

    def _parse_responses(self, text: str, docs: dict[str, Any], route: web.ControllerRoute):
        if (match := self._response_regex.match(text)) is not None:
            code = match.group(1)
            res_type = match.group(2)
            text = match.group(3)
            if 'responses' not in docs:
                docs['responses'] = {}
            response = {}
            if text:
                response['description'] = text
            if res_type:
                if self._response_returns_regex.match(res_type) is not None:
                    ref = self._build_ref(route, 'response')
                    if len(ref) > 0:
                        response['content'] = {'application/json': {'schema': ref}}
                elif (match := self._response_type_regex.match(res_type)) is not None:
                    if mime := match.group(1):
                        response['content'] = {mime: {'schema': {'type': 'string'}}}
            if len(response) > 0:
                docs['responses'][code] = response

    @staticmethod
    def _build_ref(route: web.ControllerRoute, schema_type: Literal['response', 'payload']):
        returns = route.returns
        if returns:
            ref = {'$ref': f'#/components/schemas/{schema_type}.{returns.model}.{returns.key}'}
            if returns.as_list:
                return {'type': 'array', 'items': ref}
            return ref
        return {}

    def _parse_path(self, path: str):
        parameters = []
        for match in self._path_param_regex.finditer(path):
            param, *args = match.group(1).split(':')
            parameters.append({
                'name': param,
                'in': 'path',
                'required': True
            })
        return parameters

    def _build_schemas(self):
        schemas = {}
        collections = {
            'payloads': self.context.mapper.payloads,
            'response': self.context.mapper.responses
        }
        include_defs = {'payloads': False, 'response': True}
        include_fks = {'payloads': True, 'response': False}
        for def_type, collection in collections.items():
            inc_defs = include_defs[def_type]
            inc_fks = include_fks[def_type]
            for model, key, definition in collection:
                properties = {}
                for field in definition.fields:
                    if isinstance(field, mapping.Field):
                        properties[field.name] = self._type_map[field.type]
                    elif isinstance(field, mapping.Definition):
                        if inc_defs:
                            properties[field.name] = {
                                '$ref': f'#/components/schemas/{def_type}.{field.model_name}.{field.model_key}'
                            }
                        if inc_fks and isinstance(field, mapping.Reference):
                            properties[field.foreign_key] = {
                                'type': 'int'
                            }
                    elif isinstance(field, mapping.List) and inc_defs:
                        elem = field.element
                        if isinstance(elem, mapping.Definition):
                            properties[field.name] = {
                                'type': 'array',
                                'items': {
                                    '$ref': f'#/components/schemas/{def_type}.{elem.model_name}.{elem.model_key}'
                                }
                            }
                schema = {
                    'type': 'object',
                    'properties': properties
                }
                schemas[f'{def_type}.{model}.{key}'] = schema
        return schemas

    def setup(self):
        if paths.exists(self.swagger_path):
            setup_swagger(self.context.app, swagger_url='/api', ui_version=3, swagger_from_file=self.swagger_path)
        else:
            no_docs_ctrl = NoDocsController(self.context)
            no_docs_route: web.ControllerRoute = no_docs_ctrl.get_no_docs.instantiate(controller=no_docs_ctrl)
            no_docs_route.setup()


class NoDocsController(web.Controller):
    __blnt__ = web.ControllerMetadata('no_docs', '', False, '', '/api', [])

    def __init__(self, context: 'blnt.BolinetteContext'):
        super().__init__(context)

    @get('')
    async def get_no_docs(self):
        params = {
            'name': self.context.manifest.get('name', 'Bolinette App'),
            'desc': self.context.manifest.get('desc', 'My web app built with the Bolinette framework'),
            'version': self.context.manifest.get('version', '0.0.1')
        }
        return self.response.render_template('no_docs.html.jinja2', params,
                                             self.context.internal_files_path('templates'))
