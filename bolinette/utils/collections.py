from collections.abc import Iterator
from typing import Generic, Iterable, TypeVar
from typing_extensions import override

T = TypeVar("T")


class OrderedSet(Generic[T], set[T]):
    def __init__(self, iterable: Iterable[T] | None = None, /) -> None:
        set.__init__(self, iterable or ())
        self.order: list[T] = []

    @override
    def add(self, element: T, /) -> None:
        set.add(self, element)
        self.order.append(element)

    @override
    def remove(self, element: T, /) -> None:
        super().remove(element)
        self.order.remove(element)

    @override
    def pop(self) -> T:
        element = super().pop()
        self.order.remove(element)
        return element

    def __getitem__(self, key: int) -> T:
        return self.order[key]

    @override
    def __iter__(self) -> Iterator[T]:
        return iter(self.order)
