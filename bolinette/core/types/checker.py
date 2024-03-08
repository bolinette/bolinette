from collections.abc import Callable
from typing import Any, Literal, Protocol, TypeGuard, overload

from bolinette.core import Cache, __user_cache__, meta
from bolinette.core.injection import init_method
from bolinette.core.types import Type


class TypeChecker:
    def __init__(self) -> None:
        self.validators: list[TypeCheckerWorker] = []

    @init_method
    def _init_validators(self, cache: Cache) -> None:
        validators: dict[float, TypeCheckerWorker] = {}
        for cls in cache.get(TypeCheckerWorkerMeta, hint=type[TypeCheckerWorker], raises=True):
            validator_meta = meta.get(cls, TypeCheckerWorkerMeta)
            validator = cls(self)
            validators[validator_meta.priority] = validator
        self.validators = [t[1] for t in sorted(validators.items(), key=lambda t: t[0], reverse=True)]

    @overload
    def instanceof[T](self, value: Any, of_type: type[T], /) -> TypeGuard[T]: ...

    @overload
    def instanceof[T](self, value: Any, of_type: Type[T], /) -> TypeGuard[T]: ...

    def instanceof(self, value: Any, of_type: type[Any] | Type[Any], /) -> Any:
        if not isinstance(of_type, Type):
            of_type = Type(of_type)
        for validator in self.validators:
            if validator.supports(of_type):
                return validator.validate(value, of_type)


class TypeCheckerWorkerMeta:
    def __init__(self, priority: int) -> None:
        self.priority = priority


class TypeCheckerWorker(Protocol):
    def __init__(self, checker: TypeChecker) -> None: ...

    def supports(self, of_type: Type[Any], /) -> bool: ...

    def validate(self, value: Any, of_type: Type[Any], /) -> bool: ...


def type_checker[V: TypeCheckerWorker](
    *,
    priority: int = 0,
    cache: Cache | None = None,
) -> Callable[[type[V]], type[V]]:
    def decorator(cls: type[V]) -> type[V]:
        meta.set(cls, TypeCheckerWorkerMeta(priority))
        (cache or __user_cache__).add(TypeCheckerWorkerMeta, cls)
        return cls

    return decorator


class TypedDictChecker:
    def __init__(self, checker: TypeChecker) -> None:
        self.checker = checker

    def supports(self, of_type: Type[Any], /) -> bool:
        return hasattr(of_type.cls, "__total__")

    def validate(self, value: Any, of_type: Type[Any], /) -> bool:
        if not isinstance(value, dict):
            return False
        for p_name, anno_t in of_type.annotations().items():
            if p_name not in value:
                return False
            if not self.checker.instanceof(value[p_name], anno_t):
                return False
        return True


class ProtocolTypeChecker:
    def __init__(self, checker: TypeChecker) -> None:
        self.checker = checker

    def supports(self, of_type: Type[Any], /) -> bool:
        return isinstance(of_type.cls, type) and issubclass(of_type.cls, Protocol)

    def validate(self, value: Any, of_type: Type[Any], /) -> bool:
        raise NotImplementedError()


class LiteralTypeChecker:
    def __init__(self, checker: TypeChecker) -> None:
        self.checker = checker

    def supports(self, of_type: Type[Any], /) -> bool:
        return of_type.cls is Literal

    def validate(self, value: Any, of_type: Type[Any], /) -> bool:
        return value in of_type.vars


class DefaultTypeChecker:
    def __init__(self, checker: TypeChecker) -> None:
        self.checker = checker

    def supports(self, of_type: Type[Any], /) -> bool:
        return True

    def validate(self, value: Any, of_type: Type[Any], /) -> bool:
        return isinstance(value, of_type.cls) or any(isinstance(value, t.cls) for t in of_type.union)
