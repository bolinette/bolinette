class DatabaseSection:
    name: str
    url: str
    echo: bool = False


class DataSection:
    databases: list[DatabaseSection]
