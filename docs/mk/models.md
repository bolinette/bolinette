# Models

Models represent the data structures. They are injected in the SqlAlchemy ORM and the database tables can be created
with the CLI.

Attributes are declared at class level and must be instances of
[`bolinette.types.defs.Column`](../bolinette/types/defs.py).

The first argument is an instance of [`bolinette.types.db.DataType`](../bolinette/types/db.py).
The available types are:
- `Boolean`
- `Date`
- `Email`
- `Float`
- `Integer`
- `Password`
- `String`

Using the named parameters will change how the field will be converted into a database column and how the framework
will validate the values before inserting data. The `unique` option indicates only one value is permitted in this
column; default is `False`. The `nullable` option indicates if the value can be `NULL` (`None` in Python); default
is `True`.

The `primary_key` option must only be used with an `Integer` and generates an auto-incremented identifier.

## Payloads

Payload define objects the API is expecting from the client. If the payload is declared inside the controller route,
it will be automatically validated using basic rules, like checking non-nullable fields are not empty and foreign
references exist.

You can add your own validation rules using the `validate` option by passing a function.

## Example

```python
from bolinette import types, core
from bolinette.decorators import model

@model('book')
class Book(core.Model):
    id = types.defs.Column(types.db.Integer, primary_key=True)
    name = types.defs.Column(types.db.String, unique=True, nullable=False)
    pages = types.defs.Column(types.db.Integer, nullable=False)

    @classmethod
    def payloads(cls):
        yield [
            types.mapping.Column(cls.name, required=True),
            types.mapping.Column(cls.pages, required=True)
        ]

    @classmethod
    def responses(cls):
        yield [
            types.mapping.Column(cls.name)
        ]
        yield 'complete', [
            types.mapping.Column(cls.name),
            types.mapping.Column(cls.pages)
        ]
```
