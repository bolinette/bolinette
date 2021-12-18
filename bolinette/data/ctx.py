from abc import ABC
from bolinette import data
from bolinette.core import BolinetteContext, BolinetteExtension, ExtensionContext
from bolinette.data.database import DatabaseManager


class DataContext(ExtensionContext):
    def __init__(self, ext: BolinetteExtension, context: BolinetteContext):
        super().__init__(ext, context)
        self.mapper = data.Mapper()
        self.validator = data.Validator(self.context, self)
        self.db = DatabaseManager(self.context, self)


class WithDataContext(ABC):
    def __init__(self, data_ctx: DataContext) -> None:
        self.__data_ctx__ = data_ctx

    @property
    def data_ctx(self):
        return self.__data_ctx__
