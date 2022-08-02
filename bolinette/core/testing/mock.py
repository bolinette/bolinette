from typing import Any, Generic, TypeVar

from bolinette.core import Cache, Injection, InjectionStrategy, meta
from bolinette.core.inject import InjectionContext

T = TypeVar("T")


class _MockedMeta(Generic[T]):
    def __init__(self, cls: type[T]) -> None:
        self.cls = cls
        self._attrs: dict[str, Any] = {}

    def __contains__(self, key: str) -> bool:
        return key in self._attrs

    def __getitem__(self, key: str) -> Any:
        return self._attrs[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self._attrs[key] = value


class _MockWrapper(Generic[T]):
    def __init__(
        self,
        cls: type[T],
    ) -> None:
        self._cls = self._setup_mocked_cls(cls)
        self._instance = self._cls()

    @staticmethod
    def _get_mocked_attr(cls: type[T], instance: T, name: str):
        if name == "__class__":
            return cls
        _meta = meta.get(type(instance), _MockedMeta)
        if name in _meta:
            return _meta[name]
        raise KeyError(f"'{name}' attribute has not been mocked in {cls}")

    @staticmethod
    def _setup_mocked_cls(cls: type[T]) -> type[T]:
        _t = type(f"{cls.__name__}__Mocked", (cls,), {})
        setattr(_t, "__init__", lambda _: None)
        setattr(_t, "__repr__", lambda _: f"<Mocked[{cls.__name__}]>")
        setattr(
            _t,
            "__getattribute__",
            lambda i, n: _MockWrapper._get_mocked_attr(cls, i, n),
        )
        meta.set(_t, _MockedMeta, _MockedMeta(cls))
        return _t

    def setup(self, name: str, value: Any) -> "_MockWrapper[T]":
        _meta = meta.get(self._cls, _MockedMeta)
        _meta[name] = value
        return self


class Mock:
    def __init__(
        self, *, inject: Injection | None = None, cache: Cache | None = None
    ) -> None:
        self._inject = inject or Injection(cache or Cache(), InjectionContext())
        self._mocked: dict[type[Any], _MockWrapper[Any]] = {}

    def mock(self, cls: type[T]) -> _MockWrapper[T]:
        if cls in self._mocked:
            mocked = self._mocked[cls]
        else:
            mocked = _MockWrapper(cls)
            self._mocked[cls] = mocked
            self._inject.add(
                cls, InjectionStrategy.Singleton, instance=mocked._instance
            )
        return mocked

    @property
    def injection(self) -> Injection:
        return self._inject
