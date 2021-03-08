from typing import Optional, Type, Iterator, Tuple

from bolinette import utils


class Properties:
    def __init__(self, parent: object):
        self.parent = parent

    def _get_cls_attribute_of_type(self, attr_type):
        return ((name, attribute)
                for name, attribute in vars(self.parent.__class__).items()
                if isinstance(attribute, attr_type))

    def _get_attribute_of_type(self, attr_type):
        return ((name, attribute)
                for name, attribute in vars(self.parent).items()
                if isinstance(attribute, attr_type))

    def get_proxies(self, of_type: Optional[Type] = None) -> Iterator[Tuple[str, 'utils.InitProxy']]:
        proxies = self._get_cls_attribute_of_type(utils.InitProxy)
        if of_type is not None:
            return filter(lambda p: p[1].of_type(of_type), proxies)
        return proxies
