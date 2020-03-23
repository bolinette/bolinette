from bolinette import db, transaction

from example.models import Person, Book


@db.seeder
async def seed_app():
    with transaction:
        p1 = Person(name='J.R.R. Tolkien')
        b1 = Book(name='The Fellowship of the Ring', pages=678, author=p1)
        b2 = Book(name='The Two Towers', pages=612, author=p1)
        b3 = Book(name='The Return of the King', pages=745, author=p1)
        db.session.add(p1)
        db.session.add(b1)
        db.session.add(b2)
        db.session.add(b3)
