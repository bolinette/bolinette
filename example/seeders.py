from datetime import datetime

from bolinette import transaction, db

from example.models import Person, Book


@db.engine.seeder
async def seed_app():
    with transaction:
        p1 = Person(first_name='J.R.R.', last_name='Tolkien')
        b1 = Book(name='The Fellowship of the Ring', pages=678, author=p1,
                  price=23.45, publication_date=datetime(1954, 7, 29))
        b2 = Book(name='The Two Towers', pages=612, author=p1,
                  price=24.58, publication_date=datetime(1954, 11, 11))
        b3 = Book(name='The Return of the King', pages=745, author=p1,
                  price=25.7, publication_date=datetime(1955, 10, 20))
        db.engine.session.add(p1)
        db.engine.session.add(b1)
        db.engine.session.add(b2)
        db.engine.session.add(b3)
