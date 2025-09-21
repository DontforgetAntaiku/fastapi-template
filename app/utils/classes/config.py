import logging
from typing import Optional

from dotenv import load_dotenv

from .config_factory import ConfigFactory

from ..exceptions import EnvironmentFileError


class DatabaseInfo(ConfigFactory):
    __prefix__ = "DB_"
    USER: str
    PASSWORD: Optional[str]
    HOST: str
    PORT: int
    NAME: str


class ConfInfo(ConfigFactory):
    __prefix__ = "CONF_"
    SESSION_SECRET: str
    LOGIN_SECRET: str
    ADMIN_DEFAULT_PASSWORD: str


class Config:
    database: DatabaseInfo
    configuration: ConfInfo

    def __init__(self, path: Optional[str] = None):
        try:
            load_dotenv(path)
            for attr_name, factory_cls in self.__annotations__.items():
                instance = factory_cls()
                setattr(self, attr_name, instance)
        except EnvironmentFileError as E:
            logging.error(E)
            self.create_example_env()
            raise E

    @staticmethod
    def create_example_env():
        """
        Creates an example.env file with placeholder values.
        """
        params = []
        for attr_name, factory_cls in Config.__annotations__.items():
            params.append(f"# {attr_name}")
            if not hasattr(factory_cls, "__prefix__"):
                setattr(factory_cls, "__prefix__", Config.__qualname__)
            for var_name in factory_cls.__annotations__.keys():
                params.append(f"{factory_cls.__prefix__ + var_name}=")
        with open(".env.example", "w") as file:
            file.write("\n".join(params))
        print("Created .env.example file")
