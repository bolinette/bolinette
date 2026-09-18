from pydantic import Field

from bolinette.core.configuration import config_section
from bolinette.core.mapping import BolinetteModel


class DatabaseSection(BolinetteModel):
    name: str
    url: str
    echo: bool = False


@config_section("data")
class DataSection(BolinetteModel):
    databases: list[DatabaseSection] = Field(default_factory=list[DatabaseSection])
