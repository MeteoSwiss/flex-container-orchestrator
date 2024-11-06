from pydantic import BaseModel

from flex_container_orchestrator.config.base_settings import \
    BaseServiceSettings
from flex_container_orchestrator.config.logger import LoggingSettings


class TimeSettings(BaseModel):
    # Number of hours between timesteps
    tincr: int
    # Number of timesteps to run Flexpart with (temporarily set to 6 timesteps but operational config is 90)
    tdelta: int
    # Frequency of Flexpart runs in hours
    tfreq_f: int
    # Frequency of IFS runs in hours
    tfreq: int


class AppSettings(BaseModel):
    app_name: str
    time_settings: TimeSettings


class ServiceSettings(BaseServiceSettings):
    logging: LoggingSettings
    main: AppSettings
