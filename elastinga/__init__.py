# -*- coding: utf-8 -*-
"""Inicialización del paquete"""

from elastinga.settings import init_project_settings
from elastinga._logging import configure_logging

SETTINGS = init_project_settings()

logger = configure_logging("elastinga", SETTINGS)