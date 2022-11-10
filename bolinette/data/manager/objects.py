from typing import Generic, Literal, Protocol, TypeVar

from bolinette.data import Entity


class TableColumn:
    def __init__(
        self,
        table: "TableDefinition",
        name: str,
        py_type: type,
        sql_type,
        nullable: bool,
        format: Literal["password", "email"] | None,
    ) -> None:
        self.table = table
        self.name = name
        self.py_type = py_type
        self.sql_type = sql_type
        self.nullable = nullable
        self.format = format

    def __repr__(self) -> str:
        return f"<Column {self.name}>"


class Reference(Protocol):
    table: "TableDefinition"
    name: str
    target: "TableDefinition"
    lazy: bool | Literal["subquery"]
    other_side: "CollectionReference | TableReference | None"


class TableReference(Reference):
    def __init__(
        self,
        table: "TableDefinition",
        name: str,
        target: "TableDefinition",
        lazy: bool | Literal["subquery"],
        constraint: "ForeignKeyConstraint",
    ) -> None:
        self.table = table
        self.name = name
        self.target = target
        self.lazy = lazy
        self.constraint = constraint
        self.other_side: CollectionReference | TableReference | None


class CollectionReference(Reference):
    def __init__(
        self,
        table: "TableDefinition",
        name: str,
        target: "TableDefinition",
        lazy: bool | Literal["subquery"],
    ) -> None:
        self.table = table
        self.name = name
        self.target = target
        self.lazy = lazy
        self.other_side: CollectionReference | TableReference


class Constraint(Protocol):
    table: "TableDefinition"
    name: str
    columns: list[TableColumn]


class PrimaryKeyConstraint(Constraint):
    def __init__(
        self, table: "TableDefinition", name: str, columns: list[TableColumn]
    ) -> None:
        self.table = table
        self.name = name
        self.columns = columns


class ForeignKeyConstraint(Constraint):
    def __init__(
        self,
        table: "TableDefinition",
        name: str,
        columns: list[TableColumn],
        target: "TableDefinition",
        target_columns: list[TableColumn],
    ) -> None:
        self.table = table
        self.name = name
        self.columns = columns
        self.target = target
        self.target_columns = target_columns
        self.reference: TableReference | None = None


class UniqueConstraint(Constraint):
    def __init__(
        self, table: "TableDefinition", name: str, columns: list[TableColumn]
    ) -> None:
        self.table = table
        self.name = name
        self.columns = columns


EntityT = TypeVar("EntityT", bound=Entity)
ConstraintType = UniqueConstraint | PrimaryKeyConstraint | ForeignKeyConstraint
ConstraintT = TypeVar("ConstraintT", bound=ConstraintType)


class TableDefinition(Generic[EntityT]):
    def __init__(self, name: str, entity: type[EntityT]) -> None:
        self.name = name
        self.entity = entity
        self.columns: dict[str, TableColumn] = {}
        self.references: dict[str, TableReference | CollectionReference] = {}
        self.constraints: dict[str, ConstraintType] = {}

    def get_constraints(
        self,
        of_type: type[ConstraintT],
    ) -> list[tuple[str, ConstraintT]]:
        return [(n, a) for n, a in self.constraints.items() if isinstance(a, of_type)]

    def find_constraint(self, columns: list[TableColumn]) -> ConstraintType | None:
        for const in self.constraints.values():
            for col in columns:
                if col not in const.columns:
                    break
            else:
                return const
        return None

    def get_primary_key(self) -> PrimaryKeyConstraint:
        return next(
            c for c in self.constraints.values() if isinstance(c, PrimaryKeyConstraint)
        )

    def check_unique(self, columns: list[TableColumn]) -> UniqueConstraint | None:
        for constraint in {a for _, a in self.get_constraints(UniqueConstraint)}:
            for col_def in constraint.columns:
                if col_def not in columns:
                    break
            else:
                return constraint
        return None

    def __repr__(self) -> str:
        return f"<Table {self.name}>"
