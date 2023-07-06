from collections.abc import Iterator
from typing import Generic, Iterable, TypeVar
from typing_extensions import override

T = TypeVar("T")


class OrderedSet(Generic[T], set[T]):
    def __init__(self, iterable: Iterable[T] | None = None, /) -> None:
        set.__init__(self, iterable or ())
        self._order: list[T] = []

    @override
    def add(self, element: T, /) -> None:
        set.add(self, element)
        self._order.append(element)

    @override
    def remove(self, element: T, /) -> None:
        super().remove(element)
        self._order.remove(element)

    @override
    def pop(self) -> T:
        element = super().pop()
        self._order.remove(element)
        return element

    @override
    def discard(self, element: T, /) -> None:
        super().discard(element)
        if element in self._order:
            self._order.remove(element)

    @override
    def update(self, *sets: Iterable[T]) -> None:
        super().update(*sets)
        for s in sets:
            for element in s:
                if element not in self._order:
                    self._order.append(element)

    def __getitem__(self, key: int) -> T:
        return self._order[key]

    @override
    def __iter__(self) -> Iterator[T]:
        return iter(self._order)
