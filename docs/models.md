# Models

Models represent the data structures.
Bolinette supports SQL and NoSQL databases.

> ⚠️ Relational models are attribute based, (e.g. `model.column`), but non-relational models are
> collection based (e.g. `model['column']`).
> Both types are incompatible

Here's a basic model:

```python
from bolinette import types, core
from bolinette.decorators import model

@model('book')
class Book(core.Model):
    id = types.defs.Column(types.db.Integer, primary_key=True)
    uid = types.defs.Column(types.db.String, unique=True, nullable=False, entity_key=True)
    name = types.defs.Column(types.db.String, nullable=False)
    pages = types.defs.Column(types.db.Integer, nullable=False)
    price = types.defs.Column(types.db.Float)
    publication_date = types.defs.Column(types.db.Date)
```

Almost every Bolinette class must be decorated and identified.
The string you provide in the decorator will identify this model.
Use this string to get the model from the [context](context.md).

## Columns

Attributes are declared at class level and must be instances of type
[`bolinette.types.defs.Column`](https://github.com/bolinette/bolinette/blob/master/bolinette/types/defs.py).

The first argument is an instance of type
[`bolinette.types.db.DataType`](https://github.com/bolinette/bolinette/blob/master/bolinette/types/db.py).
The available types are:
- `Boolean`
- `Date`
- `Email`
- `Float`
- `Integer`
- `Password`
- `String`

Using the named parameters will change how the field will be converted into a database column and how the framework
will validate the values before inserting data.

The `unique` option indicates all values in this column must be different; default is `False`.

The `nullable` option indicates if the value can be `NULL` (`None` in Python); default is `True`.

The `primary_key` option generates an index.
If the column is an `Integer`, it generates an auto-incremented identifier.

## Entity key

Exposing auto-incremented integer primary keys might be a security issue.
It is recommended not to include id columns in any response or payload object so that clients never see those ids.
You can mark a column as `entity_key=True`.
That column becomes the identifying key, used in automatic routing and foreign links.

An entity key must be a column marked as `unique=True`.
If no column is marked as `entity_key=True`, the primary key is used.

Let's make some http requests where our models don't use entity keys and expose auto ids.

```text
POST https://my.api.com/api/book
> {"name": "The Lord of the Rings", "author": {"id": "125"}}
< {"id": 3874, "name": "The Lord of the Rings", "author": {"id": "125", "name": "J.R.R. Tolkien"}}

GET https://my.api.com/api/book/3874
< {"id": 3874, "name": "The Lord of the Rings", "author": {"id": "125", "name": "J.R.R. Tolkien"}}
```

Now the same requests, but the two models define a `uid` entity_key.

```text
POST https://my.api.com/api/book
> {"name": "The Lord of the Rings", "author": {"uid": "21652e60"}}
< {"id": "e59f3a8b", "name": "The Lord of the Rings", "author": {"uid": "21652e60", "name": "J.R.R. Tolkien"}}

GET https://my.api.com/api/book/e59f3a8b
< {"id": "e59f3a8b", "name": "The Lord of the Rings", "author": {"uid": "21652e60", "name": "J.R.R. Tolkien"}}
```

## Relationships

Relationships can be defined between models.
Relationships between relational models will generate structural dependencies between the database tables.

> ⚠️ Relationships between collection models (NoSQL) are not supported yet.

### One to many

To define a one-to-many relationship, the child class must have a column that defines a reference the parent
class' primary key, with the same type.

From the child class, a `types.defs.Relationships` allows to access the parent class directly from an attribute.
The `lazy` attribute is false by default.
If true, the parent entity is loaded when accessed and stays unloaded until then.

To create a bidirectional relationship, specify a backref inside the `Relationship`.
`types.defs.Backref` accepts a string, the name of the list that will be injected in the parent entity.
You can also specify a `lazy` parameter.
Be sure that the lazy is not true in both the `Relationship` and the `Backref`.

```python
from bolinette import core, types
from bolinette.decorators import model

@model('parent')
class Parent(core.Model):
    id = types.defs.Column(types.db.Integer, primary_key=True, entity_key=True)

@model('child')
class Child(core.Model):
    id = types.defs.Column(types.db.Integer, primary_key=True, entity_key=True)
    parent_id = types.defs.Column(types.db.Integer, reference=types.defs.Reference('parent', 'id'))
    parent = types.defs.Relationship('parent', foreign_key=parent_id, lazy=False,
                                     backref=types.defs.Backref('children', lazy=True))
```

To define a self-referencing one-to-many relationship, don't use the `foreign_key` parameter.
Instead, pass the primary key of the table to the `remote_side` parameter.

```python
from bolinette import core, types
from bolinette.decorators import model

@model('element')
class Element(core.Model):
    id = types.defs.Column(types.db.Integer, primary_key=True, entity_key=True)
    parent_id = types.defs.Column(types.db.Integer, reference=types.defs.Reference('element', 'id'))
    parent = types.defs.Relationship('element', remote_side=id, lazy=True,
                                     backref=types.defs.Backref('children', lazy=False))
```

### Many to many

Many-to-many relationships require a pivot table.
That table is declared as `join_table=True` is the decorator and does not require an entity key.
Then use the `secondary` parameter in the `Relationship` to specify the pivot table's name.

```python
from bolinette import core, types
from bolinette.decorators import model

@model('book')
class Book(core.Model):
    id = types.defs.Column(types.db.Integer, primary_key=True, entity_key=True)

@model('author')
class Author(core.Model):
    id = types.defs.Column(types.db.Integer, primary_key=True, entity_key=True)
    books = types.defs.Relationship('book', secondary='books_authors', lazy='subquery',
                                    backref=types.defs.Backref('authors', lazy=True))

@model('books_authors', join_table=True)
class BooksAuthors(core.Model):
    book_id = types.defs.Column(types.db.Integer, reference=types.defs.Reference('book', 'id'), primary_key=True)
    author_id = types.defs.Column(types.db.Integer, reference=types.defs.Reference('author', 'id'), primary_key=True)
```

As you can see, you can also define a `Backref`, that will inject a list on the other side of the relationship.

## Payloads and Responses

### Mapping objects

Payload and responses are defined inside the model, as lists of definitions.
A definition consists of an identifying string and a list of `bolinette.mapping.MappingObject`, an abstract class.
Several subclasses are available to fit all use cases.

Here are some examples:

```python
from bolinette import mapping, types

unit_price = mapping.Field(types.db.Float, key='price')
formatted_price = mapping.Field(types.db.String, key='price', formatting=lambda price: f'{price} €')
total_price = mapping.Field(types.db.Float, name='total_price', function=lambda e: e.price * e.quantity)
author = mapping.Definition('person', 'default', key='author')
clients = mapping.List(mapping.Definition('user', 'public'), key='clients')
```

The `key` parameter is the model-side attribute.
The `name` parameter is the JSON-side attribute.
If `name` is not provided, it is the same as `key`.

The `function` parameter takes a function, with the entity as first parameter.
The `key` is ignored, so you must provide a `name`.

The `formatting` parameter takes a function, with the value as first parameter.
It is intended to apply a transformation to the value.

`mapping.Field` describes a single value, with a type.
Type checking is performed at validation, before the controller.
`mapping.Column` is a subclass that takes a `types.defs.Column`, to easily fill the type and key in.

`mapping.Definition` describes a nested object.
`mapping.Reference` is a subclass that takes a `types.defs.Relationship`.

### Payloads

Payloads define objects the API is expecting from the client.
If the payload is declared inside the controller route, it will be automatically validated using basic rules,
like checking non-nullable fields are not empty and foreign references exist.

Payloads are defined inside the `payloads` class method that must return a list of tuples.
The first element is the payload's name, the second is a list of `mapping.MappingObject`.
The name can be omitted, `"default"` is the default name.

If the `required` parameter is true, the validation will raise an error if the field is not inside the payload.

You can add your own validation rules using the `validate` option by passing a function.

The `function` and `formatting` parameters are only used for responses and are ignored in payloads.

### Responses

Responses define what the API returns to the client.
Only built-in types are JSON serializable, so returning a model or any Python class in a controller will
raise an error.
Responses describe to the framework how to serialize database entity objects.

Responses are defined inside the `responses` class method that must return a list of tuples.
The first element is the response's name, the second is a list of `mapping.MappingObject`.
The name can be omitted, `"default"` is the default name.

## Complete example

```python
from bolinette import types, core, mapping
from bolinette.decorators import model

@model('book')
class Book(core.Model):
    id = types.defs.Column(types.db.Integer, primary_key=True)
    uid = types.defs.Column(types.db.String, unique=True, nullable=False, entity_key=True)
    name = types.defs.Column(types.db.String, nullable=False)
    pages = types.defs.Column(types.db.Integer, nullable=False)
    price = types.defs.Column(types.db.Float)
    publication_date = types.defs.Column(types.db.Date)

    def payloads(self):
        yield [
            mapping.Column(self.uid, required=True),
            mapping.Column(self.name, required=True),
            mapping.Column(self.pages, required=True),
            mapping.Column(self.price),
            mapping.Column(self.publication_date)
        ]

    def responses(self):
        yield [
            mapping.Column(self.uid),
            mapping.Column(self.name)
        ]
        yield 'complete', [
            mapping.Column(self.uid),
            mapping.Column(self.name),
            mapping.Column(self.pages),
            mapping.Column(self.price),
            mapping.Column(self.publication_date)
        ]
```
