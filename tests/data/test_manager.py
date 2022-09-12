import pytest

from bolinette.core import Cache, Logger
from bolinette.core.testing import Mock
from bolinette.core.utils import AttributeUtils
from bolinette.data import (
    Backref,
    Column,
    ManyToOne,
    ModelManager,
    PrimaryKey,
    Reference,
    model,
    types,
)
from bolinette.data.exceptions import ModelError
from bolinette.data.manager import _ColumnDef


def _setup_mock(cache: Cache) -> Mock:
    mock = Mock(cache=cache)
    mock.injection.add(AttributeUtils, "singleton")
    mock.injection.add(ModelManager, "singleton")
    mock.mock(Logger).dummy()
    return mock


def test_init_model_basic_columns() -> None:
    class Test:
        id: int
        name: str
        price: float

    class TestModel:
        id = Column(types.Integer, primary_key=True)
        name = Column(types.String)
        price = Column(types.Float)

    cache = Cache()
    model(Test, cache=cache)(TestModel)
    mock = _setup_mock(cache)
    manager = mock.injection.require(ModelManager)

    assert Test in manager._models
    assert manager._models[Test].name == "test"
    assert len(manager._models[Test].attrs(_ColumnDef)) == 3
    assert "id" in manager._models[Test].attributes
    assert "name" in manager._models[Test].attributes
    assert "price" in manager._models[Test].attributes


def test_init_fail_same_entity() -> None:
    class Test:
        id: int

    class TestModel1:
        id = Column(types.Integer, primary_key=True)

    class TestModel2:
        id = Column(types.Integer, primary_key=True)

    cache = Cache()
    model(Test, cache=cache)(TestModel1)
    model(Test, cache=cache)(TestModel2)
    mock = _setup_mock(cache)

    with pytest.raises(ModelError) as info:
        mock.injection.require(ModelManager)

    assert (
        f"Model {TestModel2}, Entity {Test} is already used by model {TestModel1}"
        in info.value.message
    )


def test_fail_init_no_primary_key() -> None:
    class Test:
        id: int

    class TestModel:
        id = Column(types.Integer)

    cache = Cache()
    model(Test, cache=cache)(TestModel)
    mock = _setup_mock(cache)

    with pytest.raises(ModelError) as info:
        mock.injection.require(ModelManager)

    assert f"Model {TestModel}, No primary key defined" in info.value.message


def test_init_default_primary_key() -> None:
    class Test:
        id: int

    class TestModel:
        id = Column(types.Integer, primary_key=True)

    cache = Cache()
    model(Test, cache=cache)(TestModel)
    mock = _setup_mock(cache)

    manager = mock.injection.require(ModelManager)

    assert "test_pk" in manager._models[Test].attributes
    assert len(manager._models[Test].attributes["test_pk"].columns) == 1  # type: ignore
    assert list(map(lambda c: c.name, manager._models[Test].attributes["test_pk"].columns)) == ["id"]  # type: ignore


def test_init_default_composite_primary_key() -> None:
    class Test:
        id1: int
        id2: int

    class TestModel:
        id1 = Column(types.Integer, primary_key=True)
        id2 = Column(types.Integer, primary_key=True)

    cache = Cache()
    model(Test, cache=cache)(TestModel)
    mock = _setup_mock(cache)

    manager = mock.injection.require(ModelManager)

    assert "test_pk" in manager._models[Test].attributes
    assert len(manager._models[Test].attributes["test_pk"].columns) == 2  # type: ignore
    assert list(map(lambda c: c.name, manager._models[Test].attributes["test_pk"].columns)) == ["id1", "id2"]  # type: ignore


def test_init_manual_primary_key() -> None:
    class Test:
        id: int

    class TestModel:
        id = Column(types.Integer)
        test_custom_pk = PrimaryKey(id)

    cache = Cache()
    model(Test, cache=cache)(TestModel)
    mock = _setup_mock(cache)

    manager = mock.injection.require(ModelManager)

    assert "test_custom_pk" in manager._models[Test].attributes
    assert len(manager._models[Test].attributes["test_custom_pk"].columns) == 1  # type: ignore
    assert list(map(lambda c: c.name, manager._models[Test].attributes["test_custom_pk"].columns)) == ["id"]  # type: ignore


def test_fail_init_two_primary_keys() -> None:
    class Test:
        id: int

    class TestModel:
        id = Column(types.Integer, primary_key=True)
        test_custom_pk = PrimaryKey(id)

    cache = Cache()
    model(Test, cache=cache)(TestModel)
    mock = _setup_mock(cache)

    with pytest.raises(ModelError) as info:
        mock.injection.require(ModelManager)

    assert f"Model {TestModel}, Several primary keys cannot be defined" in info.value.message


def test_fail_init_model_entity_missing_param() -> None:
    class Test:
        id: int
        name: str

    class TestModel:
        id = Column(types.Integer, primary_key=True)
        name = Column(types.String)
        price = Column(types.Float)

    cache = Cache()
    model(Test, cache=cache)(TestModel)
    mock = _setup_mock(cache)

    with pytest.raises(ModelError) as info:
        mock.injection.require(ModelManager)

    assert (
        f"Model {TestModel}, No 'price' annotated attribute found in {Test}"
        in info.value.message
    )


def test_fail_init_model_entity_param_wrong_type() -> None:
    class Test:
        id: int
        name: bool
        price: float

    class TestModel:
        id = Column(types.Integer, primary_key=True)
        name = Column(types.String)
        price = Column(types.Float)

    cache = Cache()
    model(Test, cache=cache)(TestModel)
    mock = _setup_mock(cache)

    with pytest.raises(ModelError) as info:
        mock.injection.require(ModelManager)

    assert (
        f"Entity {Test}, Attribute 'name', Type {bool} is not assignable to column type {str}"
        in info.value.message
    )


def test_init_model_foreign_key() -> None:
    class Parent:
        id: int

    class ParentModel:
        id = Column(types.Integer, primary_key=True)

    class Child:
        id: int
        parent_id: int

    class ChildModel:
        id = Column(types.Integer, primary_key=True)
        parent_id = Column(types.Integer, reference=Reference(Parent, "id"))

    cache = Cache()
    model(Parent, cache=cache)(ParentModel)
    model(Child, cache=cache)(ChildModel)

    mock = _setup_mock(cache)
    manager = mock.injection.require(ModelManager)

    assert Parent in manager._models
    assert Child in manager._models

    assert "parent_id" in manager._models[Child].attributes
    assert manager._models[Child].attributes["parent_id"].reference is not None  # type: ignore
    assert manager._models[Child].attributes["parent_id"].reference.model.entity == Parent  # type: ignore
    assert list(map(lambda c: c.name, manager._models[Child].attributes["parent_id"].reference.columns)) == ["id"]  # type: ignore


def test_fail_init_model_wrong_foreign_key_type() -> None:
    class Parent:
        id: int

    class ParentModel:
        id = Column(types.Integer, primary_key=True)

    class Child:
        id: int
        parent_id: str

    class ChildModel:
        id = Column(types.Integer, primary_key=True)
        parent_id = Column(types.String, reference=Reference(Parent, "id"))

    cache = Cache()
    model(Parent, cache=cache)(ParentModel)
    model(Child, cache=cache)(ChildModel)

    mock = _setup_mock(cache)

    with pytest.raises(ModelError) as info:
        mock.injection.require(ModelManager)

    assert (
        f"Model {ChildModel}, Attribute 'parent_id', Type does not match referenced column type"
        in info.value.message
    )


def test_fail_init_model_unknown_model() -> None:
    class Parent:
        id: int

    class Child:
        id: int
        parent_id: int

    class ChildModel:
        id = Column(types.Integer, primary_key=True)
        parent_id = Column(types.Integer, reference=Reference(Parent, "id"))

    cache = Cache()
    model(Child, cache=cache)(ChildModel)

    mock = _setup_mock(cache)

    with pytest.raises(ModelError) as info:
        mock.injection.require(ModelManager)

    assert (
        f"Model {ChildModel}, Attribute 'parent_id', {Parent} is not known entity"
        in info.value.message
    )


def test_fail_init_model_unknown_column() -> None:
    class Parent:
        id: int

    class ParentModel:
        id = Column(types.Integer, primary_key=True)

    class Child:
        id: int
        parent_id: int

    class ChildModel:
        id = Column(types.Integer, primary_key=True)
        parent_id = Column(types.Integer, reference=Reference(Parent, "uuid"))

    cache = Cache()
    model(Parent, cache=cache)(ParentModel)
    model(Child, cache=cache)(ChildModel)

    mock = _setup_mock(cache)

    with pytest.raises(ModelError) as info:
        mock.injection.require(ModelManager)

    assert (
        f"Model {ChildModel}, Attribute 'parent_id', Target column 'uuid' does not exist on {ParentModel}"
        in info.value.message
    )


def test_init_model_many_to_ones() -> None:
    class Parent:
        id: int

    class ParentModel:
        id = Column(types.Integer, primary_key=True)

    class Child:
        id: int
        parent_id: int
        parent: Parent

    class ChildModel:
        id = Column(types.Integer, primary_key=True)
        parent_id = Column(types.Integer, reference=Reference(Parent, "id"))
        parent = ManyToOne(parent_id)

    cache = Cache()
    model(Parent, cache=cache)(ParentModel)
    model(Child, cache=cache)(ChildModel)

    mock = _setup_mock(cache)
    manager = mock.injection.require(ModelManager)

    assert Child in manager._models
    assert "parent" in manager._models[Child].attributes
    assert manager._models[Child].attributes["parent"].target.entity == Parent  # type: ignore


def test_fail_init_model_many_to_ones_missing_param() -> None:
    class Parent:
        id: int

    class ParentModel:
        id = Column(types.Integer, primary_key=True)

    class Child:
        id: int
        parent_id: int

    class ChildModel:
        id = Column(types.Integer, primary_key=True)
        parent_id = Column(types.Integer, reference=Reference(Parent, "id"))
        parent = ManyToOne(parent_id)

    cache = Cache()
    model(Parent, cache=cache)(ParentModel)
    model(Child, cache=cache)(ChildModel)
    mock = _setup_mock(cache)

    with pytest.raises(ModelError) as info:
        mock.injection.require(ModelManager)

    assert (
        f"Model {ChildModel}, No 'parent' annotated attribute found in {Child}"
        in info.value.message
    )


def test_fail_init_model_many_to_ones_wrong_type() -> None:
    class Parent:
        id: int

    class ParentModel:
        id = Column(types.Integer, primary_key=True)

    class Child:
        id: int
        parent_id: int
        parent: int

    class ChildModel:
        id = Column(types.Integer, primary_key=True)
        parent_id = Column(types.Integer, reference=Reference(Parent, "id"))
        parent = ManyToOne(parent_id)

    cache = Cache()
    model(Parent, cache=cache)(ParentModel)
    model(Child, cache=cache)(ChildModel)
    mock = _setup_mock(cache)

    with pytest.raises(ModelError) as info:
        mock.injection.require(ModelManager)

    assert (
        f"Entity {Child}, Attribute 'parent', Type {int} is not assignable to column type {Parent}"
        in info.value.message
    )


class ParentA:
    id: int
    children: "list[ChildA]"


class ParentModelA:
    id = Column(types.Integer, primary_key=True)


class ChildA:
    id: int
    parent_id: int
    parent: ParentA


class ChildModelA:
    id = Column(types.Integer, primary_key=True)
    parent_id = Column(types.Integer, reference=Reference(ParentA, "id"))
    parent = ManyToOne(parent_id, Backref("children"))


def test_init_model_many_to_ones_back_ref() -> None:
    cache = Cache()
    model(ParentA, cache=cache)(ParentModelA)
    model(ChildA, cache=cache)(ChildModelA)
    mock = _setup_mock(cache)

    mock.injection.require(ModelManager)


class ParentB:
    id: int
    children: list


class ParentModelB:
    id = Column(types.Integer, primary_key=True)


class ChildB:
    id: int
    parent_id: int
    parent: ParentB


class ChildModelB:
    id = Column(types.Integer, primary_key=True)
    parent_id = Column(types.Integer, reference=Reference(ParentB, "id"))
    parent = ManyToOne(parent_id, Backref("children"))


def test_fail_init_model_many_to_ones_back_ref_missing_generic() -> None:
    cache = Cache()
    model(ParentB, cache=cache)(ParentModelB)
    model(ChildB, cache=cache)(ChildModelB)
    mock = _setup_mock(cache)

    with pytest.raises(ModelError) as info:
        mock.injection.require(ModelManager)

    assert (
        f"Entity {ParentB}, Attribute 'children', Type {list} needs a generic argument"
        in info.value.message
    )


class ParentC:
    id: int
    children: list[int]


class ParentModelC:
    id = Column(types.Integer, primary_key=True)


class ChildC:
    id: int
    parent_id: int
    parent: ParentC


class ChildModelC:
    id = Column(types.Integer, primary_key=True)
    parent_id = Column(types.Integer, reference=Reference(ParentC, "id"))
    parent = ManyToOne(parent_id, Backref("children"))


def test_fail_init_model_many_to_ones_back_ref_wrong_generic() -> None:
    cache = Cache()
    model(ParentC, cache=cache)(ParentModelC)
    model(ChildC, cache=cache)(ChildModelC)
    mock = _setup_mock(cache)

    with pytest.raises(ModelError) as info:
        mock.injection.require(ModelManager)

    assert (
        f"Entity {ParentC}, Attribute 'children', Type list[{int}] is not assignable to column type list[{ChildC}]"
        in info.value.message
    )


def test_fail_init_model_many_to_ones_no_reference() -> None:
    class Parent:
        id: int

    class ParentModel:
        id = Column(types.Integer, primary_key=True)

    class Child:
        id: int
        parent_id: int
        parent: Parent

    class ChildModel:
        id = Column(types.Integer, primary_key=True)
        parent_id = Column(types.Integer)
        parent = ManyToOne(parent_id)

    cache = Cache()
    model(Parent, cache=cache)(ParentModel)
    model(Child, cache=cache)(ChildModel)

    mock = _setup_mock(cache)

    with pytest.raises(ModelError) as info:
        mock.injection.require(ModelManager)

    assert (
        f"Model {ChildModel}, Attribute 'parent', Given foreign key does not reference any column"
        in info.value.message
    )
