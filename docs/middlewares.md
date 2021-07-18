# Middlewares

Middlewares are functions called before the controller route.
They can be useful to factorize pre or post controller logic.
See [here](./controllers.md#using-middlewares) to know how to use middlewares.

## Default middlewares

Bolinette provides middlewares that cover basic use cases.

### Authentication

Using the `auth` middleware protects the controller or the route from being accessed by unauthenticated users.
This middleware injects the parameter `current_user`, that contains the logged-in user, into the route function.

The `optional` boolean parameter allow the request to go through the middleware even if the user is not logged in.
In that case, `current_user` will be `None`.
`optional` is false by default.

The `fresh` boolean parameter requires the user to have a fresh JWT, gotten from the login route, not refreshed.
`fresh` is false by default

The `roles` list parameter takes the names of roles that can access the route.
See [here](./authentication.md) to learn about users and roles.

Examples:
- `middlewares=['auth|fresh|roles=admin']`
- `middlewares=['auth|optional']`
- `middlewares=['auth|roles=creator,curator']`

## Middleware priority

## Custom middlewares

A middleware must be a subclass of `bolinette.web.InternalMiddleware` and decorated by `@middleware` be injectable
in controllers.

### Handle

A middleware has a `handle` method that is called before the route.
All middlewares form a chain that the request has to go through before the controller.

`handle` has three arguments.
`request` is the `aiohttp` request object, containing information about the route and the caller.
`params` is a dictionary containing all the arguments that will be
[injected in the route](./controllers.md#injected-parameters).
`next_func` is a function that calls the rest of the middleware chain.

A common error is forgetting to call `next_func` or return its return value.

### Options

Middlewares are customizable by options passed in the declaration string.
A middleware must declare the options expected.

Override the `define_options` method and returns a dictionary.
The keys are strings, the option names.
The values are instances of `MiddlewareParam`, shortcuts are found in `self.params`.

Here is the complete list:

```python
from bolinette import web
from bolinette.decorators import middleware

@middleware('example')
class ExampleMiddleware(web.Middleware):
    def define_options(self):
        return {
            'name': self.params.string(required=True),
            'optional': self.params.bool(default=True),
            'count': self.params.int(default=0),
            'threshold': self.params.float(),
            'routes': self.params.list(self.params.string(), required=True),
            'ids': self.params.list(self.params.int())
        }

    async def handle(self, request, params, next_func):
        assert self.options['name'] is not None
        assert self.options['optional'] is True or self.options['optional'] is False
        assert self.options['count'] is None or isinstance(self.options['count'], int)
        assert self.options['threshold'] is None or isinstance(self.options['threshold'], float)
        assert self.options['list'] is not None and isinstance(self.options['list'], list)
        assert self.options['ids'] is None or isinstance(self.options['ids'], list)
        return await next_func(request, params)
```

### Complete example

In this example, we track which page a user is visiting.

```python
from datetime import datetime
from bolinette import web, core, types
from bolinette.decorators import middleware, model, service, controller, get, post
from bolinette.exceptions import InternalError

@model('trace')
class Trace(core.Model):
    id = types.defs.Column(types.db.Integer, primary_key=True)
    name = types.defs.Column(types.db.String, unique=True, entity_key=True)
    visits = types.defs.Column(types.db.Integer, nullable=False)
    last_visit = types.defs.Column(types.db.Date, nullable=False)
    user_id = types.defs.Column(types.db.Integer, nullable=False, reference=types.defs.Reference('user', 'id'))
    user = types.defs.Relationship('user', foreign_key=user_id, lazy=False,
                                   backref=types.defs.Backref('traces', lazy=True))

@service('trace')
class TraceService(core.Service):
    async def inc_trace(self, page_name, user, timestamp):
        trace = await self.repo.query().filter_by({'name': page_name, 'user_id': user.id}).first()
        if trace is None:
            await self.repo.create({'name': page_name, 'visits': 1, 'last_visit': timestamp, 'user': user})
        else:
            trace.visits += 1
            trace.last_visit = timestamp

@middleware('tracking')
class TrackingMiddleware(web.Middleware):
    @property
    def trace_service(self) -> TraceService:
        return self.context.service('trace')

    def define_options(self):
        return {
            'name': self.params.string(required=True)
        }

    async def handle(self, request, params, next_func):
        if 'current_user' not in params:
            raise InternalError('auth middleware needs to be called before tracking middleware')
        current_user = params['current_user']
        page_name = self.options['name']
        await self.trace_service.inc_trace(page_name, current_user, datetime.utcnow())
        return await next_func(request, params)

@controller('book')
class BookController(web.Controller):
    @get('/{book_uid}', returns=web.Returns('book', 'complete'),
         middlewares=['auth', 'tracking|name=get_book_by_uid'])
    async def get_book(self, match):
        book_uid = match['book_uid']
        return await self.service.get_first_by('uid', book_uid)

    @post('', expects=web.Expects('book', 'complete'), returns=web.Returns('book'),
          middlewares=['auth', 'tracking|name=create_new_book'])
    async def create_book(self, payload):
        return await self.service.create(payload)
```
