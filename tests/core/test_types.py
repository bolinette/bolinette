from typing import ForwardRef, Generic, TypeVar

import pytest

from bolinette.exceptions import TypingError
from bolinette.types import Type, TypeVarLookup


def test_simple_type() -> None:
    class _T:
        pass

    t = Type(_T)

    assert t.cls is _T
    assert t.vars == ()
    assert str(t) == "test_simple_type.<locals>._T"
    assert repr(t) == "<Type test_simple_type.<locals>._T>"
    assert hash(t) == hash((_T, ()))
    assert t == Type(_T)


def test_generic_type() -> None:
    T = TypeVar("T")

    class _T(Generic[T]):
        pass

    t = Type(_T[T], raise_on_typevar=False)

    assert t.cls is _T
    assert t.vars == (T,)
    assert str(t) == "test_generic_type.<locals>._T[~T]"
    assert repr(t) == "<Type test_generic_type.<locals>._T[~T]>"
    assert hash(t) == hash((_T, (T,)))
    assert t == Type(_T[T], raise_on_typevar=False)


def test_fail_missing_generic_param() -> None:
    T = TypeVar("T")

    class _T(Generic[T]):
        pass

    with pytest.raises(TypingError) as info:
        Type(_T)

    assert (
        info.value.message == "Type test_fail_missing_generic_param.<locals>._T, All generic parameters must be defined"
    )


def test_specified_generic_type() -> None:
    T = TypeVar("T")

    class _P:
        pass

    class _T(Generic[T]):
        pass

    t = Type(_T[_P])

    assert t.cls is _T
    assert t.vars == (_P,)
    assert str(t) == "test_specified_generic_type.<locals>._T[test_specified_generic_type.<locals>._P]"
    assert hash(t) == hash((_T, (_P,)))


def test_fail_forward_ref() -> None:
    T = TypeVar("T")

    class _T(Generic[T]):
        pass

    class _P:
        pass

    with pytest.raises(TypingError) as info:
        Type(_T["_P"])

    assert info.value.message == "Type test_fail_forward_ref.<locals>._T, Generic parameter '_P' cannot be a string"


def test_forward_ref() -> None:
    T = TypeVar("T")

    class _T(Generic[T]):
        pass

    class _P:
        pass

    t = Type(_T["_P"], raise_on_string=False)

    assert t.vars == (ForwardRef("_P"),)
    assert str(t) == "test_forward_ref.<locals>._T['_P']"


def test_fail_typevar() -> None:
    T = TypeVar("T")

    class _T(Generic[T]):
        pass

    with pytest.raises(TypingError) as info:
        Type(_T[T], raise_on_typevar=True)

    assert info.value.message == "Type test_fail_typevar.<locals>._T, Generic parameter ~T cannot be a TypeVar"


def test_typvar_lookup() -> None:
    T = TypeVar("T")

    class _T(Generic[T]):
        pass

    class _K(Generic[T]):
        pass

    class _P:
        pass

    t = Type(_T[T], lookup=TypeVarLookup(Type(_K[_P])))

    assert t.vars == (_P,)


def test_fail_typvar_not_found_in_lookup() -> None:
    T = TypeVar("T")
    K = TypeVar("K")

    class _T(Generic[T]):
        pass

    class _K(Generic[K]):
        pass

    class _P:
        pass

    with pytest.raises(TypingError) as info:
        Type(_T[T], lookup=TypeVarLookup(Type(_K[_P])))

    assert (
        info.value.message
        == "Type test_fail_typvar_not_found_in_lookup.<locals>._T, TypeVar ~T could not be found in lookup"
    )


def test_typvar_not_found_in_lookup() -> None:
    T = TypeVar("T")
    K = TypeVar("K")

    class _T(Generic[T]):
        pass

    class _K(Generic[K]):
        pass

    class _P:
        pass

    k = Type(_K[_P])
    t = Type(_T[T], lookup=TypeVarLookup(k), raise_on_typevar=False)

    assert t.vars == (T,)


def test_lookup() -> None:
    T = TypeVar("T")

    class _T(Generic[T]):
        pass

    class _P:
        pass

    t = Type(_T[_P], raise_on_typevar=False)
    l = TypeVarLookup(t)

    assert not l.empty
    assert [*l] == [(T, _P)]
    assert l[T] is _P


def test_empty_lookup() -> None:
    class _T:
        pass

    t = Type(_T)
    l = TypeVarLookup(t)

    assert l.empty
    assert [*l] == []


def test_fail_lookup_key_not_found() -> None:
    T = TypeVar("T")
    K = TypeVar("K")

    class _T(Generic[T]):
        pass

    class _P:
        pass

    t = Type(_T[_P], raise_on_typevar=False)
    l = TypeVarLookup(t)

    with pytest.raises(KeyError):
        l[K]
