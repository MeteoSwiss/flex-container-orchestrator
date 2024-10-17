from pydantic import BaseModel

from flex_container_orchestrator.config.logger import LoggingSettings
from flex_container_orchestrator.config.base_settings import BaseServiceSettings


class AppSettings(BaseModel):
    """The main application settings"""
    app_name: str


class ServiceSettings(BaseServiceSettings):
    logging: LoggingSettings
    main: AppSettings
