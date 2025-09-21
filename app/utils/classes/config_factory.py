import os
import typing
from abc import ABC

from ..exceptions import InvalidEnvironmentError, NoParameterError


class ConfigFactory(ABC):
    def __init__(self):
        if not hasattr(self, "__prefix__"):
            self.__prefix__ = self.__qualname__
        for var_name, var_type in self.__annotations__.items():
            env_value = os.getenv(self.__prefix__ + var_name, "")

            origin = typing.get_origin(var_type)
            args = typing.get_args(var_type)
            is_optional = origin is typing.Union and type(None) in args
            if is_optional:
                base_type = next(t for t in args if t is not type(None))
            else:
                base_type = var_type
            if env_value == "":
                if is_optional:
                    setattr(self, var_name, None)
                    continue
                raise NoParameterError(
                    f"Environment variable '{self.__prefix__ + var_name}' not set"
                )
            try:
                setattr(self, var_name, self._cast_value(env_value, base_type))
            except ValueError:
                raise InvalidEnvironmentError(
                    f"Environment variable '{self.__prefix__ + var_name}' has an invalid value"
                )

    def _cast_value(self, value: str, var_type: type):
        if var_type is str:
            return value
        elif var_type is int:
            return int(value)
        elif var_type is bool:
            return value.lower() in ("true", "1", "yes")
        elif var_type in (list[int], tuple[int]):
            return (
                tuple(map(int, value.split(",")))
                if var_type is tuple[int]
                else list(map(int, value.split(",")))
            )
        elif var_type in (list[str], tuple[str]):
            return (
                tuple(value.split(",")) if var_type is tuple[str] else value.split(",")
            )
        elif var_type in (list[bool], tuple[bool]):
            return (
                tuple(
                    map(lambda x: x.lower() in ("true", "1", "yes"), value.split(","))
                )
                if var_type is tuple[bool]
                else list(
                    map(lambda x: x.lower() in ("true", "1", "yes"), value.split(","))
                )
            )
        raise TypeError(f"Unsupported type: {var_type}")
