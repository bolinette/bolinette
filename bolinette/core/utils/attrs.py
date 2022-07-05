import itertools
from collections.abc import Iterator
from typing import TypeVar

_T = TypeVar("_T")


def get_cls_attributes_of_type(
    obj: type, attr_type: type[_T]
) -> Iterator[tuple[str, _T]]:
    parent_attrs = (
        get_cls_attributes_of_type(parent, attr_type) for parent in obj.__bases__
    )
    return itertools.chain(
        *parent_attrs,
        (
            (name, attribute)
            for name, attribute in vars(obj).items()
            if isinstance(attribute, attr_type)
        )
    )


def get_attributes_of_type(obj, attr_type):
    return (
        (name, attribute)
        for name, attribute in vars(obj).items()
        if isinstance(attribute, attr_type)
    )
