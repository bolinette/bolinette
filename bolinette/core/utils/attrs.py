import itertools
from typing import Any, Iterable, TypeVar

InstanceT = TypeVar("InstanceT")


class AttributeUtils:
    @staticmethod
    def get_cls_attrs(
        obj: type[Any],
        *,
        of_type: type[InstanceT] | tuple[type[InstanceT], ...] | None = None
    ) -> Iterable[tuple[str, InstanceT]]:
        parent_attrs = (
            AttributeUtils.get_cls_attrs(parent, of_type=of_type)
            for parent in obj.__bases__
        )
        return itertools.chain(
            *parent_attrs,
            (
                (name, attribute)
                for name, attribute in vars(obj).items()
                if of_type is None or isinstance(attribute, of_type)
            )
        )

    @staticmethod
    def get_instance_attrs(obj: Any, *, of_type: type[Any] | None = None):
        return (
            (name, attribute)
            for name, attribute in vars(obj).items()
            if of_type is None or isinstance(attribute, of_type)
        )
