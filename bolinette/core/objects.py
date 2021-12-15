from typing import Any


class Pagination:
    def __init__(self, items: list[Any], page: int, per_page: int, total: int):
        self.items = items
        self.page = page
        self.per_page = per_page
        self.total = total

    def __repr__(self) -> str:
        return f'<Pagination {self.page}:{self.per_page} {len(self.items)}/{self.total}>'


class PaginationParams:
    def __init__(self, page: int, per_page: int):
        self.page = page
        self.per_page = per_page

    def __repr__(self):
        return f'<Pagination {self.page}:{self.per_page}>'


class OrderByParams:
    def __init__(self, column: str, ascending: bool):
        self.column = column
        self.ascending = ascending

    def __repr__(self):
        return f'<OrderBy {self.column}:{"asc" if self.ascending else "desc"}>'
