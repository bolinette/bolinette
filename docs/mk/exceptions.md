# Exceptions

Any request can be aborted at any time by raising an Error.
The error is caught at top level and a readable error is sent to the client.
All errors are located inside the [`bolinette.exceptions`](../bolinette/exceptions.py) package and inherit `APIError`.

## Error codes

By default, an `APIError` generates a 500 error.
There are other errors that inherit from this class and send different error codes:

- 400 `BadRequestError`
- 401 `UnauthorizedError`
- 403 `ForbiddenError`
- 404 `NotFoundError`
- 409 `ConflictError`

These errors take a message in their constructor that will be sent in the response.
They have more specific subclasses for more specific use cases.

- `EntityNotFoundError(NotFoundError) __init__(model, key, value)`
- `ParamMissingError(BadRequestError) __init__(key)`
- `ParamConflictError(ConflictError) __init__(key, value)`

## Multiple errors

To send multiple error messages to the client, use `APIErrors`.

```python
from bolinette.exceptions import APIErrors, EntityNotFoundError, ParamMissingError

errors = APIErrors()
errors.append(EntityNotFoundError(model='book', key='id', value=99))
errors.append(ParamMissingError(key='price'))
raise errors
```
