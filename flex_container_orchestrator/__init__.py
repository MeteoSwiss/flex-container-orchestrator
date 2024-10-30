""" Initializations """

import os
from dotenv import load_dotenv

from flex_container_orchestrator.config import logger
from flex_container_orchestrator.config.service_settings import ServiceSettings

load_dotenv(os.path.join(os.path.dirname(__file__), 'config/.env')) # Load .env variables

# mypy: ignore-errors
CONFIG = ServiceSettings(
    "settings.yaml", os.path.join(os.path.dirname(__file__), "config")
)

# Configure logger
logger.apply_logging_settings(CONFIG.logging)
