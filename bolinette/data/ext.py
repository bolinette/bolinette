from collections.abc import Callable
from typing import Literal, TypeVar

from bolinette.core import BolinetteContext, BolinetteExtension, BolinetteCache
from bolinette.data import (
    DataContext,
    Mixin,
    MixinMetadata,
    MixinServiceMethod,
    SimpleService,
    ServiceMetadata,
    Seeder,
)
from bolinette.data.models import Model, ModelMetadata, ModelProperty

T_Model = TypeVar("T_Model", bound=Model)
T_Mixin = TypeVar("T_Mixin", bound=Mixin)
T_Service = TypeVar("T_Service", bound=SimpleService)


class DataExtension(BolinetteExtension[DataContext]):
    def __init__(self):
        super().__init__()
        self.mixin = _MixinDecorator(self._cache)
        self.model = _ModelDecorator(self._cache)

    def __create_context__(self, context: BolinetteContext) -> DataContext:
        return DataContext(self, context)

    @property
    def __context_type__(self):
        return DataContext

    def service(self, service_name: str, *, model_name: str = None):
        def decorator(service_cls: type[T_Service]) -> type[T_Service]:
            service_cls.__blnt__ = ServiceMetadata(
                service_name, model_name or service_name
            )
            self._cache.push(service_cls, "service", service_name)
            return service_cls

        return decorator

    def seeder(self, func: Callable[[BolinetteContext], None]):
        seeder = Seeder(func)
        self.cache.push(seeder, "seeder", seeder.name)
        return func


class _MixinDecorator:
    def __init__(self, cache: BolinetteCache) -> None:
        self._cache = cache

    def __call__(self, mixin_name: str):
        def decorator(mixin_cls: type[T_Mixin]) -> type[T_Mixin]:
            mixin_cls.__blnt__ = MixinMetadata(mixin_name)
            self._cache.push(mixin_cls, "mixin", mixin_name)
            return mixin_cls

        return decorator

    @staticmethod
    def service_method(func: Callable):
        return MixinServiceMethod(func.__name__, func)


class _ModelDecorator:
    def __init__(self, cache: BolinetteCache) -> None:
        self._cache = cache

    def __call__(
        self,
        model_name: str,
        *,
        mixins: list[str] = None,
        database: str = "default",
        model_type: Literal["relational", "collection"] = "relational",
        definitions: Literal["ignore", "append", "overwrite"] = "ignore",
        join_table: bool = False
    ):
        def decorator(model_cls: type[T_Model]) -> type[T_Model]:
            model_cls.__blnt__ = ModelMetadata(
                model_name,
                database,
                model_type == "relational",
                join_table,
                mixins or [],
                definitions,
            )
            self._cache.push(model_cls, "model", model_name)
            return model_cls

        return decorator

    def property(self, function):
        return ModelProperty(function.__name__, function)


ext = DataExtension()
