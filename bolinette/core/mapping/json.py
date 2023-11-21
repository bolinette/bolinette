import json
from collections.abc import Iterable
from typing import Any, override


class JsonObjectEncoder(json.JSONEncoder):
    @override
    def default(self, o: Any) -> Any:
        return self.obj_to_primitives(o)

    def obj_to_primitives(self, o: object) -> Any:
        if isinstance(o, int | float | bool | str):
            return o
        if isinstance(o, Iterable):
            return list(*o)
        return {k: v for k, v in vars(o).items()}
