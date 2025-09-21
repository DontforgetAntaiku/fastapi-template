import logging
import os
from typing import Final

from fastapi.templating import Jinja2Templates

from app.utils.classes.config import Config

DEBUG = True


LOG_LEVEL: Final[int] = logging.ERROR
WORK_DIR: Final[str] = os.path.dirname(__file__)

CONFIG: Final = Config(".env")

TEMPLATES = Jinja2Templates(directory="templates")
