# Services

Services contain the business logic of the application.
We recommend writing all the logic inside the services, to keep the controllers as simple as possible.

Here's a basic example:

```python
from bolinette import core
from bolinette.decorators import service

@service('book')
class BookService(core.Service):
    def __init__(self, context):
        super().__init__(context)
```

Services are identified by a string.
That string is used to get the service form the [context](context.md).
By default, the service supposes that a model with the same name exists.
You can use the `model_name` parameter inside the decorator to use another model.

## Default methods

The `Service` base class provides a set of methods to create, update, delete and retrieve entities.
All base methods are asynchronous, don't forget to await them, or create an asyncio task.

- `async get(id, *, safe=False)` returns the entity which corresponds to the id provided.
  The method throws a `EntityNotFoundError` if no entity is found.
  Use `safe=True` to return `None` if not found.
- `async get_by(key, value)` returns all entities which `key` column equals to `value`.
  Returns an empty list if no entity is found.
- `async get_first_by(key, value, *, safe=False)` returns the first entity which `key` column equals to `value`.
  The method throws a `EntityNotFoundError` if no entity is found.
  Use `safe=True` to return `None` if not found.
- `async get_all(*, pagination=None, order_by=None)` returns the complete list of entities in the table.
  See [Pagination](#pagination) for details about the `pagination` parameter.
  See [Order](#order) for details about the `order` parameter.
- `async create(values)` inserts a new entity in the database.
  `values` is expected to be a dictionary, with the columns as keys and their respective values.
  The inserted entity is returned by this method.
- `async update(entity, values)` modifies the entity with the given values.
  All columns are updated and missing ones are interpreted as a `None` value.
  `entity` has to be a database entity that comes from a get method.
  The method returns the updated entity.
- `async patch(entity, values)` modifies the entity, but skips missing columns in the `values` dictionary.
- `async delete(entity)` removes an entity from the database and returns it.
  `entity` has to be a database entity that comes from a get method.
  
## Overriding methods

It is possible to override a default method to customize its behavior, like adding more validation.
Be sure to call the base method or the [underlying repository method](./repositories.md#basic-interactions) to
complete the process.

```python
from typing import Dict, Any
from bolinette import core
from bolinette.decorators import service
from bolinette.exceptions import APIError

class TooExpensiveError(APIError):
  def __init__(self, message):
    super().__init__(message, name="TooExpensiveError")

@service('product')
class ProductService(core.Service):
    async def create(self, values: Dict[str, Any]):
        if values['price'] * values['quantity'] >= 100:
            raise TooExpensiveError('Whoa, that\'s way too expensive!')
        values['status'] = 'OK'
        return await super().create(values)
```

## Pagination

Some methods support pagination.
These methods expect an instance of
[`bolinette.blnt.objects.PaginationParams`](https://github.com/bolinette/bolinette/blob/master/bolinette/blnt/objects.py),
with a page number and per page count.
First page is number 0.

These methods will not return a list as usual, but will return an instance of
[`bolinette.blnt.objects.Pagination`](https://github.com/bolinette/bolinette/blob/master/bolinette/blnt/objects.py).
This object gives you the entities inside the `items` attribute.
The attributes `page`, `per_page` and `total` give additional information about the current page and the total
count of entities in the table.

You can return a `Pagination` directly from a controller, the framework will handle that and send the pagination back,
nicely serialized.

```python
from bolinette import core
from bolinette.decorators import service
from bolinette.blnt.objects import PaginationParams

@service('book')
class BookService(core.Service):
    async def get_paginated_books(self):
        params = PaginationParams(page=1, per_page=10) # Requests second page
        result = await self.get_all(pagination=params)
        print(result.page) # "1"
        print(result.per_page) # "10"
        print(result.total) # whatever the total is
        print(len(result.items)) # "10" or less, possibly empty
        return result
```

## Order

Some methods support ordering entities.
These methods expect a list of
[`bolinette.blnt.objects.OrderByParams`](https://github.com/bolinette/bolinette/blob/master/bolinette/blnt/objects.py),
This object specifies which column is sorted and if the order is ascending or not.

```python
from bolinette import core
from bolinette.decorators import service
from bolinette.blnt.objects import OrderByParams

@service('book')
class BookService(core.Service):
    async def get_ordered_books(self):
        params = [
          OrderByParams('price', ascending=True),
          OrderByParams('publication_date', ascending=False)
        ]
        result = await self.get_all(order_by=params)
        # entities in result will be ordered according to the parameters passed to the method
        return result
```

## NoSQL models

Keep in mind that collection-based models are Python dictionaries, which bracket-accessed attributes,
e.g. `book['price']`.
When writing custom methods in a service for one type of model, the service will be incompatible with the other
model type, due to that difference in accessing column values.

## Service without a model

Create a subclass of `bolinette.core.SimpleService` to create a service that does not require a model.
Simple services come with no base methods.

```python
import requests
from bolinette import core
from bolinette.decorators import service


@service('url')
class UrlService(core.SimpleService):
    def __init__(self, context):
        super().__init__(context)

    async def get_json_from_url(self, url: str):
        return requests.get(url).json()
```

## Call another service

Get another service from the [context](./context.md).
In the following example, here are 2 ways to call another service, by a property or via direct access in the method.
As the order in which the constructors are called is absolutely not guarantied, do not get services from the context
inside the `__init__` method.

```python
from bolinette import core
from bolinette.decorators import service

@service('person')
class PersonService(core.Service):
    pass

@service('library')
class LibraryService(core.Service):
    pass

@service('book')
class BookService(core.Service):
    def __init__(self, context):
      super().__init__(context)

    @property
    def person_service(self) -> PersonService:
        return self.context.service('person')

    @property
    def library_service(self) -> LibraryService:
        return self.context.service('library')

    async def add_book(self, title, username, author_id, library_id):
        author = await self.person_service.get(author_id)
        user = await self.context.service('user').get_by_username(username)
        library = await self.library_service.get(library_id)
        return await self.create({ 'title': title, 'author': author, 'library': library, 'created_by': user })
```
