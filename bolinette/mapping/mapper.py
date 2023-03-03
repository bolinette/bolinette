from typing import TypeVar

from bolinette import __core_cache__, injectable
from bolinette.utils import AttributeUtils

InstanceT = TypeVar("InstanceT")
DestT = TypeVar("DestT", bound=object | dict)


@injectable(cache=__core_cache__, strategy="singleton")
class Mapper:
    def __init__(self, attrs: AttributeUtils) -> None:
        self._attrs = attrs

    def map(self, src: dict | object, dest: DestT | type[DestT]) -> DestT:
        return  # type: ignore
