import re
from collections.abc import Callable
from typing import Literal

from bolinette.core import meta

HttpMethod = Literal["GET", "POST", "PUT", "PATCH", "DELETE"]
path_re = re.compile(r"\{([^}]+)\}")


class RouteProps:
    def __init__(self, method: HttpMethod, path: str) -> None:
        self.method = method
        self.real_path = path
        self.anon_path, self.url_to_func_args, self.func_to_url_args = self.build_anon_path(path)

    @staticmethod
    def build_anon_path(path: str) -> tuple[str, dict[str, str], dict[str, str]]:
        new_path: list[str] = []
        last_pos = 0
        anon_to_param: dict[str, str] = {}
        param_to_anon: dict[str, str] = {}
        for index, match in enumerate(path_re.finditer(path)):
            start, end = match.span()
            new_path.append(path[last_pos:start])
            anon_param = f"_p{index}"
            anon_to_param[anon_param] = match.group(1)
            param_to_anon[match.group(1)] = anon_param
            new_path.append(f"{{{anon_param}}}")
            last_pos = end
        new_path.append(path[last_pos:])
        return "".join(new_path), anon_to_param, param_to_anon


class RouteBucket:
    def __init__(self, name: str) -> None:
        self.name = name
        self.routes: list[RouteProps] = []

    def add(self, route: RouteProps) -> None:
        self.routes.append(route)

    def __getitem__(self, index: int) -> RouteProps:
        return self.routes[index]


def route[**FuncP, FuncT](
    method: HttpMethod,
    path: str,
    /,
) -> Callable[[Callable[FuncP, FuncT]], Callable[FuncP, FuncT]]:
    def decorator(func: Callable[FuncP, FuncT]) -> Callable[FuncP, FuncT]:
        if not meta.has(func, RouteBucket):
            bucket = RouteBucket(func.__name__)
            meta.set(func, bucket)
        else:
            bucket = meta.get(func, RouteBucket)
        bucket.add(RouteProps(method, path))
        return func

    return decorator


def get[**FuncP, FuncT](path: str, /) -> Callable[[Callable[FuncP, FuncT]], Callable[FuncP, FuncT]]:
    return route("GET", path)


def post[**FuncP, FuncT](path: str, /) -> Callable[[Callable[FuncP, FuncT]], Callable[FuncP, FuncT]]:
    return route("POST", path)


def put[**FuncP, FuncT](path: str, /) -> Callable[[Callable[FuncP, FuncT]], Callable[FuncP, FuncT]]:
    return route("PUT", path)


def patch[**FuncP, FuncT](path: str, /) -> Callable[[Callable[FuncP, FuncT]], Callable[FuncP, FuncT]]:
    return route("PATCH", path)


def delete[**FuncP, FuncT](path: str, /) -> Callable[[Callable[FuncP, FuncT]], Callable[FuncP, FuncT]]:
    return route("DELETE", path)
