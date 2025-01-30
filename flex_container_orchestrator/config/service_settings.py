from pydantic import BaseModel

from flex_container_orchestrator.config.base_settings import \
    BaseServiceSettings
from flex_container_orchestrator.config.logger import LoggingSettings


class TimeSettings(BaseModel):
    # Number of hours between timesteps
    tincr: int
    # Number of timesteps to run Flexpart with
    tdelta: int
    # Frequency of Flexpart runs in hours
    tfreq_f: int
    # Frequency of IFS runs in hours
    tfreq: int

class DBTableSettings(BaseModel):
    path: str
    name: str

class AppSettings(BaseModel):
    app_name: str
    time_settings: TimeSettings
    db: DBTableSettings

class ServiceSettings(BaseServiceSettings):
    logging: LoggingSettings
    main: AppSettings
