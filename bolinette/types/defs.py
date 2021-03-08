from typing import Optional, Any, Literal, Union

from bolinette import types, core
from bolinette.utils import InitProxy


class Reference:
    def __new__(cls, model_name: str, column_name: str) -> InitProxy['core.models.Reference']:
        return InitProxy(core.models.Reference, model_name=model_name, column_name=column_name)


class Column:
    def __new__(cls, data_type: 'types.db.DataType', *,
                reference: Optional['core.models.Reference'] = None,
                primary_key: bool = False,
                nullable: bool = True,
                unique: bool = False,
                model_id: bool = False,
                default: Optional[Any] = None) -> InitProxy['core.models.Column']:
        return InitProxy(core.models.Column, data_type=data_type, reference=reference, primary_key=primary_key,
                         nullable=nullable, unique=unique, model_id=model_id, default=default)


class Backref:
    def __new__(cls, key: str, *, lazy: bool = True) -> InitProxy['core.models.Backref']:
        return InitProxy(core.models.Backref, key=key, lazy=lazy)


class Relationship:
    def __new__(cls, model_name: str, *,
                backref: 'core.models.Backref' = None,
                foreign_key: 'core.models.Column' = None,
                lazy: Union[bool, Literal['subquery']] = False,
                secondary: str = None,
                remote_side: 'core.models.Column' = None) -> InitProxy['core.models.Relationship']:
        return InitProxy(core.models.Relationship, model_name=model_name, backref=backref, foreign_key=foreign_key,
                         lazy=lazy, secondary=secondary, remote_side=remote_side)
