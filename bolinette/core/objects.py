from typing import Any, override


class GenericMeta:
    def __init__(self, args: tuple[Any, ...]) -> None:
        self._args = args

    def __len__(self, /) -> int:
        return len(self._args)

    def __getitem__(self, index: int, /) -> Any:
        return self._args[index]

    @override
    def __hash__(self) -> int:
        return hash(self._args)

    @override
    def __eq__(self, value: object, /) -> bool:
        if isinstance(value, GenericMeta):
            return self._args == value._args
        if isinstance(value, tuple):
            return self._args == value
        raise TypeError(type(value))
