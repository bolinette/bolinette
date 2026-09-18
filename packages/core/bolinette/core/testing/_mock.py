from collections.abc import Callable
from typing import Any, get_args, get_origin

from soupape import ServiceCollection

from bolinette.core import meta
from bolinette.core.expressions import ExpressionNode, ExpressionTree


class _MockedMeta[MockedT]:
    KEY = "__blnt_testing_mock_meta__"

    def __init__(self, cls: type[MockedT]) -> None:
        self.cls = cls
        self.dummy = False
        self._attrs: dict[str, Any] = {}

    def _get_dummy(self, key: str) -> Callable[..., None] | None:
        if hasattr(self.cls, key) and callable(getattr(self.cls, key)):
            return lambda *args, **kwargs: None
        return None

    def __contains__(self, key: str) -> bool:
        return key in self._attrs or self.dummy

    def __getitem__(self, key: str) -> Any:
        if key not in self._attrs and self.dummy:
            return self._get_dummy(key)
        return self._attrs[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self._attrs[key] = value


class _MockWrapper[MockedT]:
    def __init__(
        self,
        cls: type[MockedT],
    ) -> None:
        self._cls = self._setup_mocked_cls(cls)
        self.instance = self._cls()

    @staticmethod
    def _get_mocked_attr(_cls: type[MockedT], instance: MockedT, name: str) -> Any:
        if name == "__class__":
            return _cls
        _meta = meta.get(type(instance), _MockedMeta.KEY)
        if name in _meta:
            return _meta[name]
        raise KeyError(f"'{name}' attribute has not been mocked in {_cls}")

    @staticmethod
    def _setup_mocked_cls(_cls: type[MockedT]) -> type[MockedT]:
        def _get_attr(instance: object, name: str) -> Any:
            return _MockWrapper._get_mocked_attr(_cls, instance, name)  # pyright: ignore[reportUnknownMemberType]

        _t = type(f"{_cls.__name__}__Mocked", (_cls,), {})
        _t.__init__ = lambda _: None  # pyright: ignore[reportAttributeAccessIssue]
        _t.__repr__ = lambda _: f"<Mocked[{_cls.__name__}]>"  # pyright: ignore[reportAttributeAccessIssue]
        _t.__getattribute__ = _get_attr
        meta.set(_t, _MockedMeta.KEY, _MockedMeta(_cls))
        return _t  # pyright: ignore

    def setup_callable[**FuncP, FuncT](
        self,
        func: Callable[[MockedT], Callable[FuncP, FuncT]],
        value: Callable[FuncP, FuncT],
        /,
    ) -> "_MockWrapper[MockedT]":
        return self.setup(func, value)

    def setup[SetupT](self, func: Callable[[MockedT], SetupT], value: SetupT, /) -> "_MockWrapper[MockedT]":
        expr: ExpressionNode = func(ExpressionTree.new())  # pyright: ignore
        ExpressionTree.ensure_attribute_chain(expr)
        name = ExpressionTree.get_attribute(expr)
        _meta = meta.get(self._cls, _MockedMeta.KEY)
        _meta[name] = value
        return self

    def dummy(self, value: bool = True) -> "_MockWrapper[MockedT]":
        _meta = meta.get(self._cls, _MockedMeta.KEY)
        _meta.dummy = value
        return self


class Mock:
    def __init__(self, services: ServiceCollection) -> None:
        self._services = services
        self._mocked: dict[type[Any], _MockWrapper[Any]] = {}

    @property
    def services(self) -> ServiceCollection:
        return self._services

    @staticmethod
    def _get_generic_params[MockedT](
        _cls: type[MockedT],
    ) -> tuple[type[MockedT], tuple[Any, ...]]:
        if origin := get_origin(_cls):
            params: tuple[Any, ...] = ()
            for arg in get_args(_cls):
                params = (*params, arg)
            return origin, params
        return _cls, ()

    def mock[MockedT](self, cls: type[MockedT], *, match_all: bool = False) -> _MockWrapper[MockedT]:
        origin, _ = self._get_generic_params(cls)
        if origin in self._mocked:
            mocked = self._mocked[origin]
        else:
            mocked = _MockWrapper(origin)
            self._mocked[origin] = mocked

            def resolve_mock():
                return mocked.instance

            self._services.add_singleton(cls, resolve_mock)
        return mocked
