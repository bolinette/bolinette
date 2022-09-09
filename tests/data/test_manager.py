import pytest

from bolinette.core import Cache
from bolinette.core.testing import Mock
from bolinette.core.utils import AttributeUtils
from bolinette.data import (
    Backref,
    Column,
    ManyToOne,
    ModelManager,
    Reference,
    model,
    types,
)
from bolinette.data.exceptions import ModelError


def _setup_mock(cache: Cache) -> Mock:
    mock = Mock(cache=cache)
    mock.injection.add(AttributeUtils, "singleton")
    mock.injection.add(ModelManager, "singleton")
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
    assert len(manager._models[Test].attributes) == 3
    assert "id" in manager._models[Test].attributes
    assert "name" in manager._models[Test].attributes
    assert "price" in manager._models[Test].attributes


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
        id = Column(types.Integer)
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
    assert manager._models[Child].attributes["parent_id"].reference.column.name == "id"  # type: ignore


def test_fail_init_model_unknown_model() -> None:
    class Parent:
        id: int

    class Child:
        id: int
        parent_id: int

    class ChildModel:
        id = Column(types.Integer)
        parent_id = Column(types.Integer, reference=Reference(Parent, "id"))

    cache = Cache()
    model(Child, cache=cache)(ChildModel)

    mock = _setup_mock(cache)

    with pytest.raises(ModelError) as info:
        mock.injection.require(ModelManager)

    assert (
        f"Model {ChildModel}, Column 'parent_id', {Parent} is not known entity"
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
        id = Column(types.Integer)
        parent_id = Column(types.Integer, reference=Reference(Parent, "uuid"))

    cache = Cache()
    model(Parent, cache=cache)(ParentModel)
    model(Child, cache=cache)(ChildModel)

    mock = Mock(cache=cache)
    mock.injection.add(AttributeUtils, "singleton")
    mock.injection.add(ModelManager, "singleton")

    with pytest.raises(ModelError) as info:
        mock.injection.require(ModelManager)

    assert (
        f"Model {ChildModel}, Column 'parent_id', Target column 'uuid' does not exist on {ParentModel}"
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
        id = Column(types.Integer)
        parent_id = Column(types.Integer, reference=Reference(Parent, "id"))
        parent = ManyToOne(Parent, parent_id)

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
        id = Column(types.Integer)
        parent_id = Column(types.Integer, reference=Reference(Parent, "id"))
        parent = ManyToOne(Parent, parent_id)

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
        id = Column(types.Integer)
        parent_id = Column(types.Integer, reference=Reference(Parent, "id"))
        parent = ManyToOne(Parent, parent_id)

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


class Parent:
    id: int
    children: "list[Child]"


class ParentModel:
    id = Column(types.Integer, primary_key=True)


class Child:
    id: int
    parent_id: int
    parent: Parent


class ChildModel:
    id = Column(types.Integer)
    parent_id = Column(types.Integer, reference=Reference(Parent, "id"))
    parent = ManyToOne(Parent, parent_id, Backref("children"))


def test_init_model_many_to_ones_back_ref() -> None:
    cache = Cache()
    model(Parent, cache=cache)(ParentModel)
    model(Child, cache=cache)(ChildModel)
    mock = _setup_mock(cache)

    mock.injection.require(ModelManager)


class Parent2:
    id: int
    children: list


class ParentModel2:
    id = Column(types.Integer, primary_key=True)


class Child2:
    id: int
    parent_id: int
    parent: Parent2


class ChildModel2:
    id = Column(types.Integer)
    parent_id = Column(types.Integer, reference=Reference(Parent2, "id"))
    parent = ManyToOne(Parent2, parent_id, Backref("children"))


def test_fail_init_model_many_to_ones_back_ref_missing_generic() -> None:
    cache = Cache()
    model(Parent2, cache=cache)(ParentModel2)
    model(Child2, cache=cache)(ChildModel2)
    mock = _setup_mock(cache)

    with pytest.raises(ModelError) as info:
        mock.injection.require(ModelManager)

    assert (
        f"Entity {Parent2}, Attribute 'children', Type {list} needs a generic argument"
        in info.value.message
    )


class Parent3:
    id: int
    children: list[int]


class ParentModel3:
    id = Column(types.Integer, primary_key=True)


class Child3:
    id: int
    parent_id: int
    parent: Parent3


class ChildModel3:
    id = Column(types.Integer)
    parent_id = Column(types.Integer, reference=Reference(Parent3, "id"))
    parent = ManyToOne(Parent3, parent_id, Backref("children"))


def test_fail_init_model_many_to_ones_back_ref_wrong_generic() -> None:
    cache = Cache()
    model(Parent3, cache=cache)(ParentModel3)
    model(Child3, cache=cache)(ChildModel3)
    mock = _setup_mock(cache)

    with pytest.raises(ModelError) as info:
        mock.injection.require(ModelManager)

    assert (
        f"Entity {Parent3}, Attribute 'children', Type list[{int}] is not assignable to column type list[{Child3}]"
        in info.value.message
    )
