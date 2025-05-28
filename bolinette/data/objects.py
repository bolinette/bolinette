from dataclasses import dataclass


@dataclass
class DatabaseSection:
    name: str
    url: str
    echo: bool = False


@dataclass
class DataSection:
    databases: list[DatabaseSection]
