from pydantic import BaseModel

from flex_container_orchestrator.config.base_settings import \
    BaseServiceSettings
from flex_container_orchestrator.config.logger import LoggingSettings


class TimeSettings(BaseModel):
    tincr: int
    tdelta: int
    tfreq_f: int
    tfreq: int


class AppSettings(BaseModel):
    app_name: str
    time_settings: TimeSettings


class ServiceSettings(BaseServiceSettings):
    logging: LoggingSettings
    main: AppSettings
