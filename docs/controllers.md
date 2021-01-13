# Controllers

Controllers are the entry point of a Bolinette application.
They define routes that are called by http calls from the client.

Here's a basic example:

```python
from bolinette import web
from bolinette.decorators import controller, get

@controller('home', '/home')
class HomeController(web.Controller):
    @get('')
    async def get_version(self):
        return self.response.ok(data='My API v1.0.0')

    @get(r'/hello/{name}')
    async def get_book(self, match):
        name = int(match['name'])
        return self.response.ok(data=f'Hello {name}! Nice to see you.')
```

**You should return data from a controller using the `self.response` methods.**
Any data returned directly is assumed to be a 200 response.

## Injected parameters

You can use a series of parameters that are automatically injected in the controller methods.
Parameters order has no importance, the arguments are identified by name.

- `match` is a dictionary that contains the parameters parsed in the url.
  E.g. `'/user/{username}'`: with request `'/user/bob'`, `match` will be `{'username': 'bob'}`
- `query` is a dictionary that contains the parameters in the query string.
  E.g. with query string `?p1=hello&p2=world`, `query` will be `{'p1': 'hello', 'p2': 'world'}`
- `request` is the request object from aiohttp.
  This is an instance of `aiohttp.web_request.Request`.
- `headers` is a dictionary containing the request's headers
- `payload` contains the body of the request.
  It is either the parsed JSON body or a dict from a `multipart/form-data` body.Run server
  
## Responses

Responses definitions are declared [inside the model](./models.md#responses).
Each route must declare what definition it returns in order to serialize the response.

The response is given to the route decorator and is an instance of `bolinette.web.Returns`.
This object expects two parameters.
The first one is the model's name.
The second is the response's name, default is `default`.

```python
from bolinette import web
from bolinette.decorators import controller, get

@controller('book', '/book')
class BookController(web.Controller):
    @get('', returns=web.Returns('book', as_list=True))
    async def get_books(self):
        return self.response.ok(data=await self.service.get_all())

    @get(r'/{book_uid}', returns=web.Returns('book', 'complete', skip_none=True))
    async def get_book(self, match):
        book_uid = match['book_uid']
        return self.response.ok(data=await self.service.get_first_by('uid', book_uid))
```

Use the parameter `as_list` if you want to return a collection of entities in the controller.
The `skip_none` parameter drops the null attributes during serialization.

If you don't want to use the response system, be sure to only return built-in types, as classes are not
serializable.
Any error during the JSON serialization will raise a 500 error to the client.

## Payloads

Checking the route parameters for null values and wrong formats can be a really repetitive task.
The framework provides an easy way to validate the data that comes from the client.
The payloads definitions are declared [inside the model](./models.md#payloads).

The payload is given to the route decorator and is an instance of `bolinette.web.Expects`.
This object expects two parameters.
The first one is the model's name.
The second is the payload's name, default is `default`.

```python
from bolinette import web
from bolinette.decorators import controller, put, post, patch

@controller('book', '/book')
class BookController(web.Controller):
    @post('', expects=web.Expects('book'), returns=web.Returns('book'))
    async def create_book(self, payload):
        return self.response.created(messages='Book created', data=await self.service.create(payload))

    @put(r'/{book_uid}', expects=web.Expects('book'), returns=web.Returns('book', 'complete'))
    async def update_book(self, match, payload):
        book_uid = match['book_uid']
        book = await self.service.get_first_by('uid', book_uid)
        return self.response.ok(messages=f'Book {book_uid} updated', data=await self.service.update(book, payload))

    @patch(r'/{book_uid}', expects=web.Expects('book', patch=True), returns=web.Returns('book', 'complete'))
    async def update_book_partial(self, match, payload):
        book_uid = match['book_uid']
        book = await self.service.get_first_by('uid', book_uid)
        return self.response.ok(messages=f'Book {book_uid} patched', data=await self.service.patch(book, payload))
```

By default, columns marked as `required` will raise an error if not present in the payload.
Use the `patch` parameter to ignore these missing attributes.

## HTTP methods

Decorators must be used above asynchronous methods inside a controller.
A single method can be decorated more than once, with different or identical http methods.

```python
from bolinette import web
from bolinette.decorators import controller, get

@controller('home', '/home')
class HomeController(web.Controller):
    @get('/hello/{name}')
    @get('/hello/{name}/{age}')
    async def get_version(self, match):
        message = f'Hello {match["name"]}!'
        if 'age' in match:
            message += f' You are {match["age"]}!'  
        return self.response.ok(data=message)
```

### GET

The `get` decorator binds the method to a `GET` http call.
As a `GET` request does not have a body, the `payload` route parameter is always an empty dictionary, and the
decorator has no `expects` argument.

`GET` routes are meant to retrieve resources.

### POST

The `post` decorator binds the method to a `POST` http call.

`POST` routes are meant to create new resources.

### PUT

The `put` decorator binds the method to a `PUT` http call.

`PUT` routes are meant to modify existing resources.
All attributes are usually expected and supposed null if not present.

### PATCH

The `patch` decorator binds the method to a `PATCH` http call.

`PATCH` routes are meant to modify existing resources.
Only modified attributes are usually expected, missing ones should stay untouched.

### DELETE

The `delete` decorator binds the method to a `DELETE` http call.
As a `DELETE` request does not have a body, the `payload` parameter is always an empty dictionary, and the
decorator has no `expects` argument.

`DELETE` is meant to delete resources.

### Complete example

```python
from bolinette import web
from bolinette.decorators import controller, get, post, patch, put, delete

@controller('book', '/book')
class BookController(web.Controller):
    @get(r'/{book_uid}', returns=web.Returns('book', 'complete'))
    async def get_book(self, match):
        book_uid = match['book_uid']
        return self.response.ok(data=await self.service.get_first_by('uid', book_uid))

    @post('', expects=web.Expects('book'), returns=web.Returns('book'))
    async def create_book(self, payload):
        return self.response.created(messages='Book created', data=await self.service.create(payload))

    @put(r'/{book_uid}', expects=web.Expects('book'), returns=web.Returns('book', 'complete'))
    async def update_book(self, match, payload):
        book_uid = match['book_uid']
        book = await self.service.get_first_by('uid', book_uid)
        return self.response.ok(messages=f'Book {book_uid} updated', data=await self.service.update(book, payload))

    @patch(r'/{book_uid}', expects=web.Expects('book', patch=True), returns=web.Returns('book', 'complete'))
    async def update_book_partial(self, match, payload):
        book_uid = match['book_uid']
        book = await self.service.get_first_by('uid', book_uid)
        return self.response.ok(messages=f'Book {book_uid} patched', data=await self.service.patch(book, payload))

    @delete(r'/{book_uid}', returns=web.Returns('book', 'complete'))
    async def delete_book(self, match):
        book_uid = match['book_uid']
        book = await self.service.get_first_by('uid', book_uid)
        return self.response.ok(messages=f'Book {book_uid} patched', data=await self.service.delete(book))
```

## Default routes

To avoid writing the same controllers over and over again, Bolinette provides a set of defaults route that
cover most basic use cases.

Simply override the `default_routes` method and return the list of default routes to use.
Here is the complete list:

```python
from bolinette import web
from bolinette.decorators import controller

@controller('book', '/book')
class BookController(web.Controller):
    def default_routes(self):
        return [
            self.defaults.get_all(),
            self.defaults.get_one('complete', key='uid'),
            self.defaults.create('complete', key='uid'),
            self.defaults.update('complete', key='uid'),
            self.defaults.patch('complete', key='uid'),
            self.defaults.delete('complete', key='uid')
        ]
```

All methods expect a response name as the first parameter, default is `default`.

Methods with a payload (`create`, `update` and `patch`) expect a payload name as the second parameter,
default is `default`.

Methods that require an identifier (all but `get_all` and `create`) have an optional `key` argument.
The argument is `None` by default, in which case the key will be the name of the model's
[model_id](./models.md#model-id) column.

## Using middlewares

A [middleware](./middlewares.md) can be defined in the controller decorator, or the route decorator.
The `middlewares` arguments expects a list of strings.
These strings are the declaration strings, which contain the middleware name and some options.

Options are separated by a pipe character (`|`).
An option is composed of a name and a value, separated by an equal sign (`=`)

A middleware defined in the controller can be removed in a route by prefixing an exclamation mark (`!`) to the name.

```python
from bolinette import web
from bolinette.decorators import controller, get

@controller('book', '/book', middlewares=['auth']) # every route calls the auth middleware
class BookController(web.Controller):
    def default_routes(self):
        return [
            # This route does not call the auth middleware
            self.defaults.get_one(middlewares=['!auth']),
            # This route is restricted to admins
            self.defaults.create('complete', middlewares=['auth|roles=admin'])
        ]

    # Here we use two custom middlewares
    @get('/author/{uid}', middlewares=['my-mdw1|opt|opt2=val2', 'my-mdw2|opt=val1,val2'])
    async def get_books_by_author(self, match):
        author_uid = match['uid']
        author = self.context.service('person').get_by('uid', author_uid)
        return await self.response.ok(data=await self.service.get_by('author_id', author.id))
```
