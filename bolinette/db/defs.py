from sqlalchemy import Table, Column, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, backref

from bolinette import db


class DatabaseDefs:
    def __init__(self):
        self.Session = sessionmaker()
        self.model = declarative_base()
        self.table = Table
        self.relationship = relationship
        self.backref = backref

    def column(self, col_type: db.TypeClasses.DataType, col_rel: db.TypeClasses.ForeignKey = None, *,
               name=None, primary_key=False, nullable=True, unique=False):
        db_type = col_type.sql_alchemy_type
        db_rel = None
        if isinstance(col_rel, db.TypeClasses.ForeignKey):
            db_rel = ForeignKey(f'{col_rel.model}.{col_rel.key}')
        if name:
            return Column(name, db_type, db_rel, primary_key=primary_key, nullable=nullable, unique=unique,
                          comment=str(col_type))
        return Column(db_type, db_rel, primary_key=primary_key, nullable=nullable, unique=unique,
                      comment=str(col_type))


defs = DatabaseDefs()
