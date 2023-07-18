from typing import Any, TypeVar

InstanceT = TypeVar("InstanceT")


class AttributeUtils:
    @staticmethod
    def get_cls_attrs(
        obj: type[Any], *, of_type: type[InstanceT] | tuple[type[InstanceT], ...] | None = None
    ) -> dict[str, InstanceT]:
        parent_attrs: dict[str, Any] = {}
        for parent in obj.__bases__:
            parent_attrs |= AttributeUtils.get_cls_attrs(parent, of_type=of_type)
        return parent_attrs | {
            name: attribute
            for name, attribute in vars(obj).items()
            if of_type is None or isinstance(attribute, of_type)
        }

    @staticmethod
    def get_instance_attrs(obj: object, *, of_type: type[InstanceT] | None = None) -> dict[str, InstanceT]:
        return {
            name: attribute
            for name, attribute in vars(obj).items()
            if of_type is None or isinstance(attribute, of_type)
        }
