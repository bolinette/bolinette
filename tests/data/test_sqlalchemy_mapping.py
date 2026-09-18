"""The SQLAlchemy mapping protocol and entity validation."""

from datetime import datetime

import pytest
from peritype import wrap_type
from sqlalchemy import ForeignKey, func
from sqlalchemy.orm import DeclarativeBase, Mapped, column_property, mapped_column, relationship

from bolinette.core.mapping import ABSENT, Generation
from bolinette.data import SqlAlchemyProtocol
from bolinette.data._mapping import validate_entity
from bolinette.data.exceptions import ColumnNotNullableError, EntityValidationError


class Base(DeclarativeBase):
    pass


class Author(Base):
    __tablename__ = "authors"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column()
    bio: Mapped[str | None]
    created: Mapped[datetime] = mapped_column(server_default=func.now())
    updated: Mapped[datetime | None] = mapped_column(onupdate=func.now())
    score: Mapped[int] = mapped_column(default=0)
    shout: Mapped[str] = column_property(func.upper(name))
    books: Mapped[list["Book"]] = relationship(back_populates="author")


class Book(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str]
    author_id: Mapped[int] = mapped_column(ForeignKey("authors.id"))
    author: Mapped[Author] = relationship(back_populates="books")


class Plain:
    pass


class TestProtocol:
    def test_matches_declarative_classes_only(self) -> None:
        """The protocol claims declarative classes and nothing else."""
        protocol = SqlAlchemyProtocol()

        assert protocol.matches(wrap_type(Author))
        assert not protocol.matches(wrap_type(Plain))
        assert not protocol.matches(wrap_type(int | str))
        assert protocol.fields(wrap_type(Plain)) == {}

    def test_column_specs(self) -> None:
        """Columns report nullability, generation and writability from the SQLAlchemy metadata."""
        specs = SqlAlchemyProtocol().fields(wrap_type(Author))

        assert specs["id"].generation is Generation.SERVER_GENERATED
        assert not specs["id"].writable
        assert specs["name"].generation is Generation.NONE
        assert specs["name"].writable
        assert not specs["name"].nullable
        assert specs["bio"].nullable
        assert specs["created"].generation is Generation.SERVER_GENERATED
        assert not specs["updated"].writable
        assert specs["score"].generation is Generation.CLIENT_DEFAULT
        assert specs["score"].has_default
        assert specs["score"].type.matches(int)
        assert not specs["shout"].writable
        assert specs["shout"].has_default

    def test_relationship_specs(self) -> None:
        """Relationships are lazy, not writable, and nullable when they hold a single object."""
        author_specs = SqlAlchemyProtocol().fields(wrap_type(Author))
        book_specs = SqlAlchemyProtocol().fields(wrap_type(Book))

        assert author_specs["books"].lazy
        assert not author_specs["books"].writable
        assert not author_specs["books"].nullable
        assert book_specs["author"].nullable

    def test_read_field(self) -> None:
        """Set attributes are read, attributes never set or not loaded are absent."""
        protocol = SqlAlchemyProtocol()
        specs = protocol.fields(wrap_type(Author))
        author = Author(name="Ann")

        assert protocol.read_field(author, specs["name"]) == "Ann"
        assert protocol.read_field(author, specs["bio"]) is ABSENT
        author.bio = None
        assert protocol.read_field(author, specs["bio"]) is None
        assert protocol.read_field(object(), specs["name"]) is ABSENT

    def test_construct_and_merge(self) -> None:
        """Entities are built from keyword values and list collections are merged in place."""
        protocol = SqlAlchemyProtocol()

        author = protocol.construct(wrap_type(Author), {"name": "Ann"})
        assert isinstance(author, Author) and author.name == "Ann"
        with pytest.raises(TypeError):
            protocol.construct(wrap_type(int | str), {})

        existing = [1]
        assert protocol.merge_collection(existing, [2, 3]) is existing
        assert existing == [2, 3]
        assert protocol.merge_collection((1,), [2]) == [2]


class TestValidateEntity:
    def test_valid_entity(self) -> None:
        """Server-generated and defaulted columns may be unset."""
        validate_entity(Author(name="Ann"))

    def test_missing_required_column(self) -> None:
        """An unset non-nullable column without any default is reported."""
        with pytest.raises(EntityValidationError, match=r"1 validation error.*\n  - Column 'title'") as info:
            validate_entity(Book(author_id=1))

        assert info.value.entity is Book
        assert [e.column for e in info.value.errors if isinstance(e, ColumnNotNullableError)] == ["title"]

    def test_all_missing_columns_reported_at_once(self) -> None:
        """Every missing required column is collected into a single error."""
        with pytest.raises(EntityValidationError, match="2 validation error") as info:
            validate_entity(Book())

        columns = [e.column for e in info.value.errors if isinstance(e, ColumnNotNullableError)]
        assert columns == ["title", "author_id"]
