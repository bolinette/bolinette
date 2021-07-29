import itertools
from collections.abc import Iterator
from typing import Optional

from bolinette import utils


class Properties:
    def __init__(self, parent):
        self.parent = parent

    @staticmethod
    def _get_cls_attributes_of_type(obj: type, attr_type):
        parent_attrs = (Properties._get_cls_attributes_of_type(parent, attr_type) for parent in obj.__bases__)
        return itertools.chain(
            *parent_attrs,
            ((name, attribute) for name, attribute in vars(obj).items() if isinstance(attribute, attr_type))
        )

    @staticmethod
    def _get_attributes_of_type(obj, attr_type):
        return ((name, attribute)
                for name, attribute in vars(obj).items()
                if isinstance(attribute, attr_type))

    def get_proxies(self, of_type: Optional[type] = None) -> Iterator[tuple[str, 'utils.InitProxy']]:
        proxies = self._get_cls_attributes_of_type(type(self.parent), utils.InitProxy)
        if of_type is not None:
            return filter(lambda p: p[1].of_type(of_type), proxies)
        return proxies
