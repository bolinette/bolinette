# Repositories

Each service has a repository under the hood.
This is where the actual data processing logic is.
The repository is created automatically, so you don't have to declare it.
Relational and collection-based models use the same service class, but two different repository classes.

## Basic interactions

Each [default method](./services.md#default-methods) in a service actually calls a method of the repository,
with the same name and signature.
These methods have the same behavior except the retrieve methods that do not raise exceptions when no entity is found.

To access the repository from a service, just use `self.repo`.
Note that all these methods are asynchronous.

```python
from bolinette import core
from bolinette.decorators import service

@service('book')
class BookService(core.Service):
    async def get_one_book_by_author(self, author, use_repo: bool):
        if use_repo:
            # will return None if no entity is found
            result = await self.repo.get_first_by('author_id', author.id)
        else:
            # will raise an EntityNotFoundError if no entity is found
            result = await self.get_first_by('author_id', author.id)
        return result
```

## Queries

Default methods can only find all records or filter them by one column.
Making more advanced filtering in code is not a good practice as the whole list of entities is loaded in memory.
This is where queries come in handy.

Call the repository's `query()` method to create a new query.

Then use the following methods to apply changes to the query:

- `filter_by(**kwargs)` apply equality clauses based on the names parameters and their value.
- ` filter(self, function)` apply where clauses defined in the function passed.
  See examples below.
- `order_by(column, *, desc=False)` apply a sort clause, defined by the column's name.
  Use the `desc` parameter to reverse the sort.
- `offset(offset)` skips a number of records in the request.
- `limit(limit)` limits the number of records returned by the request

Then use one of these methods to execute the query:

- `async all()` returns all entities that matched the query.
- `async first()` returns the first entity that matched the query.

```python
from bolinette import core
from bolinette.decorators import service

@service('book')
class BookService(core.Service):
    async def queries(self):
        # All books from author #1 and exactly 200 pages
        await self.repo.query().filter_by(author_id=1, pages=200).all()
        # All books from author #2 and over 300 pages
        await self.repo.query().filter_by(author_id=2).filter(lambda b: b.pages > 300).all()
        # Order books by price descending, skip 10 and take 5
        await self.repo.query().order_by('price', desc=True).offset(10).limit(5).all()
        # All books over 350 pages that cost less than 30
        await self.repo.query().filter(lambda b: b.pages > 350 and b.price < 30).all()
        # The cheapest book in the database
        await self.repo.query().order_by('price').first()
        # The biggest book from author #1
        await self.repo.query().filter_by(author_id=1).order_by('pages', desc=True).first()
```
