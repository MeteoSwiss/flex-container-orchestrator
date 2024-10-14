from pydantic import BaseModel

from mchpy.audit.logger import LoggingSettings
from mchpy.config.base_settings import BaseServiceSettings


class AppSettings(BaseModel):
    """The main application settings"""
    app_name: str


class ServiceSettings(BaseServiceSettings):
    logging: LoggingSettings
    main: AppSettings
