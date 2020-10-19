# Context

The context is a meta object available from almost every bolinette class (except models).
From the context, you can access every registered model, service and controller with the identifier string.
For example, you can call a service from a controller or another service with
`self.context.service('service_name').service_method()`.

## Aiohttp application

The underlying aiohttp application is available through `context.app`.
You can find the complete documentation [here](https://docs.aiohttp.org/en/stable/web.html).

## Environment

TODO

## Custom registration

You can inject you own objects inside the context and use them across the Bolinette classes.
Use the bracket operator to set and get objects in the context.
It is a good practice to use [init functions](./init.md) to set objects in the context.
You can use such objects as a state manager but remember that web API calls are concurrent and can corrupt your data
structures if called at the same time.

### Example
```python
from bolinette import blnt
from bolinette.decorators import init_func, service

class CustomState:
    def __init__(self):
        self._calls = 0

    def count_calls(self):
        self._calls += 1

@init_func
def init_fn(context):
    context['state'] = CustomState()

@service('book')
class BookService(blnt.Service):
    def __init__(self, context):
        super().__init__(context)

    async def create(self, values):
        self.context['state'].count_calls()
        await super().create(values)
```
