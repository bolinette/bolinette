from dataclasses import dataclass


@dataclass(init=False)
class DatabaseSection:
    name: str
    url: str
    echo: bool = False


@dataclass(init=False)
class DataSection:
    databases: list[DatabaseSection]
