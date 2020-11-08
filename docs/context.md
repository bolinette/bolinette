# Context

The context is a meta object available from almost every bolinette class (except models).
From the context, you can access every registered model, service and controller with the identifier string.
For example, you can call a service from a controller or another service with `self.context.service('service_name').service_method()`.

## Aiohttp application

The underlying aiohttp application is available through `context.app`.
You can find the complete documentation [here](https://docs.aiohttp.org/en/stable/web.html).

## Environment

[Environment variables](./environment.md#environment-variables) are available from the context, with the string key.
Internal Bolinette settings can be customized with variables like `PORT`, `HOST` and `SECRET_KEY`.
You can also use your own variables.

Variables are available from `context.env` with the brackets operator.

### Example

```yaml
# env.production.yaml
OVERRIDE_BOOK_PRICE: true
DEFAULT_BOOK_PRICE: 14.99
```

```python
from bolinette import core
from bolinette.decorators import service

@service('book')
class BookService(core.Service):
    def create(self, values):
        if self.context.env['OVERRIDE_BOOK_PRICE']:
            values['price'] = self.context.env['DEFAULT_BOOK_PRICE']
        super().create(values)
```

## Custom registration

You should avoid using global static objects.
You can inject your own objects inside the context and use them across the Bolinette classes.

Use the bracket operator to set and get objects in the context.
It is a good practice to use [init functions](./init.md) to set objects in the context.

### Example

The following piece of code is a very simple example to demonstrate how to inject custom objects.
Keep in mind that context objects will be created in every worker and stored data in context will be different in every thread.
In the example, the counter will be different in every worker and will not accurately count the API calls.

```python
from bolinette import core
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
class BookService(core.Service):
    def __init__(self, context):
        super().__init__(context)

    async def create(self, values):
        self.context['state'].count_calls()
        await super().create(values)
```
