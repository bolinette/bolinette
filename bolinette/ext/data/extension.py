from bolinette import Extension, core_ext
from bolinette.ext.data import __data_cache__

data_ext = Extension(__data_cache__, [core_ext])
