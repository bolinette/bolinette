import contextlib
import functools
import os
from collections.abc import Awaitable, Callable, Generator
from tempfile import TemporaryDirectory
from typing import Any, get_args, get_origin

from bolinette.core import Cache, meta
from bolinette.core.expressions import ExpressionNode, ExpressionTree
from bolinette.core.injection import Injection
from bolinette.core.injection.pool import InstancePool


class _MockedMeta[MockedT]:
    def __init__(self, cls: type[MockedT]) -> None:
        self.cls = cls
        self.dummy = False
        self._attrs: dict[str, Any] = {}

    def _get_dummy(self, key: str) -> None | Callable[..., None]:
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
        _meta = meta.get(type(instance), _MockedMeta[Any])
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
        meta.set(_t, _MockedMeta(_cls))
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
        _meta = meta.get(self._cls, _MockedMeta[Any])
        _meta[name] = value
        return self

    def dummy(self, value: bool = True) -> "_MockWrapper[MockedT]":
        _meta = meta.get(self._cls, _MockedMeta[Any])
        _meta.dummy = value
        return self


class Mock:
    def __init__(self, *, inject: Injection | None = None, cache: Cache | None = None) -> None:
        self._inject = inject or Injection(cache or Cache(), InstancePool())
        self._mocked: dict[type[Any], _MockWrapper[Any]] = {}

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
            self._inject.add_singleton(cls, instance=mocked.instance, match_all=match_all)
        return mocked

    @property
    def injection(self) -> Injection:
        return self._inject


@contextlib.contextmanager
def tmp_cwd() -> Generator[str, Any, None]:
    original_cwd = os.getcwd()
    with TemporaryDirectory() as tmp_dir:
        os.chdir(tmp_dir)
        try:
            yield tmp_dir
        finally:
            os.chdir(original_cwd)


def with_tmp_cwd[**P, T](func: Callable[P, T]) -> Callable[P, T]:
    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        with tmp_cwd():
            return func(*args, **kwargs)

    return wrapper


def with_tmp_cwd_async[**P, T](func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
    @functools.wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        with tmp_cwd():
            return await func(*args, **kwargs)

    return wrapper
