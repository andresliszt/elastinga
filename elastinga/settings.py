# -*- coding: utf-8 -*-
"""Project settings"""
import os
import logging
from enum import Enum
from enum import IntEnum
from pathlib import Path
from typing import Optional
from typing import Union

from dotenv import find_dotenv
from dotenv import load_dotenv

from pydantic import BaseSettings

from elastinga.exc import EnvVarNotFound


class LogLevel(IntEnum):
    """Explicitly define allowed logging levels."""

    CRITICAL = logging.CRITICAL
    ERROR = logging.ERROR
    WARNING = logging.WARNING
    INFO = logging.INFO
    DEBUG = logging.DEBUG
    TRACE = 1 + logging.NOTSET
    NOTSET = logging.NOTSET


class LogDest(Enum):
    """Define allowed destinations for logs."""

    CONSOLE = "CONSOLE"
    """Log to console"""

    FILE = "FILE"
    """Log to file"""


class LogFormatter(Enum):
    """Define allowed destinations for logs."""

    JSON = "JSON"
    """JSONs, eg for filebeat or similar, for machines"""

    COLOR = "COLOR"
    """pprinted, colored, for humans"""


class Settings(BaseSettings):
    """Configuraciones comumnes."""

    ELASTICSEARCH_HOST: str

    ELASTICSEARCH_USER: Optional[str]

    ELASTICSEARCH_PASSWORD: Optional[str]

    INSTAGRAM_INDEX_NAME: str

    FACEBOOK_INDEX_NAME: str

    TWITTER_INDEX_NAME: str

    ELASTICSEARCH_SSL_CERT_PATH: Optional[Path]

    class Config:
        env_prefix = "ELASTINGA_"


class Production(Settings):
    """Configuraciones ambiente de producción."""

    LOG_FORMAT: str = LogFormatter.JSON.value
    LOG_LEVEL: int = LogLevel.TRACE.value
    LOG_DESTINATION: str = LogDest.FILE.value


class Development(Settings):
    """Configuraciones ambiente de desarrollo."""

    LOG_FORMAT: str = LogFormatter.COLOR.value  # requires colorama
    LOG_LEVEL: int = LogLevel.INFO.value
    LOG_DESTINATION: str = LogDest.CONSOLE.value


def init_project_settings(mode="Development"):
    """Returns settings via project mode env var"""

    if mode == "Development":
        return Development()

    elif mode == "Production":
        return Production()

    else:
        raise ValueError("mode debe ser `Development` o `Production`")
