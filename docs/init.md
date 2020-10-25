# Init functions

Bolinette initialises itself through init functions. Init functions are decorated with `bolinette.decorators.init_func`.
An init function must accept one argument, which is the current context.
You can use them to create objects to be used during Bolinette's lifecycle, like creating a file, opening a connection or getting data.

Try not to use global objects. Pass these objects down to the controllers and services through the context
(see [Context](./context.md#custom-registration)).

Init functions are called in order of loading, make sure the scripts are loaded the way you want if you have init
functions in different files.

## Example

```python
from bolinette import core, blnt
from bolinette.decorators import init_func, service

@init_func
def my_init_func(context: core.context):
    context['calls'] = 0

@service('book')
class BookService(blnt.Service):
    def __init__(self, context):
        super().__init__(context)

    async def create(self, values):
        self.context['calls'] += 1
        await super().create(values)
```
