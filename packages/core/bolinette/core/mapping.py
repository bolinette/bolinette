from escondite import Cache
from muotti import Mapper
from muotti.pydantic import PydanticValueConverter
from pydantic import BaseModel


class BolinetteModel(BaseModel):
    pass


def resolve_mapper(cache: Cache) -> Mapper:
    mapper = Mapper(PydanticValueConverter())
    mapper.load_from_cache(cache)
    return mapper
