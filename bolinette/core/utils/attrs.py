from typing import Any, overload


class AttributeUtils:
    @overload
    @staticmethod
    def get_cls_attrs(obj: type[Any], *, of_type: None = None) -> dict[str, Any]: ...

    @overload
    @staticmethod
    def get_cls_attrs[InstanceT](obj: type[Any], *, of_type: type[InstanceT]) -> dict[str, InstanceT]: ...

    @staticmethod
    def get_cls_attrs[InstanceT](
        obj: type[Any],
        *,
        of_type: type[InstanceT] | None = None,
    ) -> dict[str, InstanceT]:
        parent_attrs: dict[str, Any] = {}
        for parent in obj.__bases__:
            parent_attrs |= AttributeUtils.get_cls_attrs(parent, of_type=of_type)
        return parent_attrs | {
            name: attribute
            for name, attribute in vars(obj).items()
            if of_type is None or isinstance(attribute, of_type)
        }
