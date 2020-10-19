# Cache

The cache is a static global object used to store most classes and functions decorated by a bolinette decorator.
The cache is used internally during init phase to instantiate classes like models, services and controllers.
The cache only stores types, not instantiated objects.

In normal circumstances, you should not have to use the cache.

## Example
```python
from bolinette.core import cache

srv = cache.services  # Dict[str, Type['blnt.Service']]
ctrl = cache.controllers  # Dict[str, Type['blnt.Controller']]
```
