""" Initializations """

import os

from flex_container_orchestrator.config import logger
from flex_container_orchestrator.config.service_settings import ServiceSettings

# mypy: ignore-errors
CONFIG = ServiceSettings(
    "settings.yaml", os.path.join(os.path.dirname(__file__), "config")
)

# Configure logger
logger.apply_logging_settings(CONFIG.logging)
