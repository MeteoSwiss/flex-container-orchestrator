"""
Note: This script from mchpy (MeteoSwiss Blueprint) was added here because I couldn't install mchpy from outside of the MeteoSwiss network.

Logging configuration including http request auditing
"""
import logging.config
import time
from enum import Enum
from typing import Any, Sequence

from pydantic import BaseModel, field_validator
from pydantic_settings import SettingsConfigDict
from pythonjsonlogger import jsonlogger

from flex_container_orchestrator.config import http_audit

_logger: dict = {
    'version': 1,
    # without the following option, using apply_logging_settings too late is dangerous because all loggers which were
    # previously known would be silently disabled
    'disable_existing_loggers': False,
    'filters': {
        'standard_request_id': {
            '()': 'flex_container_orchestrator.config.logger.StandardRequestIdFilter',
        },
        'json_request_id': {
            '()': 'flex_container_orchestrator.config.logger.JsonRequestIdFilter',
        },
    },
    'formatters': {
        'standard': {
            'format': '{asctime} {request_id}{levelname:>8s} {process} --- [{threadName:>15s}] {name_with_func:40}: '
                      '{message}',
            'style': '{'
        },
        'json': {
            '()': 'flex_container_orchestrator.config.logger.LogstashJsonFormatter'
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'DEBUG',
            'filters': ['standard_request_id'],
            'formatter': 'standard',
        },
    },
    'loggers': {},
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG',
    },
}


class LogLevel(str, Enum):
    """
    Wrapper class for Python logging levels so that we can make sure that no unknown logging level is taken.
    """
    CRITICAL = 'CRITICAL'
    ERROR = 'ERROR'
    WARNING = 'WARNING'
    INFO = 'INFO'
    DEBUG = 'DEBUG'
    NOTSET = 'NOTSET'


class FormatterType(str, Enum):
    """
    Wrapper class for the formatters we provide
    """
    STANDARD = 'standard'
    JSON = 'json'


class LoggingSettings(BaseModel):
    """
    This class defines the structure for our logging configuration.

    As formatters, both standard and json formatting can be chosen.
    The supported logging levels are: CRITICAL, ERROR, WARNING, INFO, DEBUG, NOTSET. These levels can be set for the
    root logger or for specific child loggers.

    As a default, the root logging level DEBUG and the standard formatter are taken.
    """
    model_config = SettingsConfigDict(extra='forbid')

    formatter: FormatterType = FormatterType.STANDARD
    root_log_level: LogLevel = LogLevel.DEBUG
    child_log_levels: dict[str, LogLevel] = {}

    @field_validator('child_log_levels')
    def logger_name_does_not_contain_reserved_key(cls, child_log_levels: dict[str, LogLevel]) -> dict[str, LogLevel]:
        for key in child_log_levels.keys():
            if key in ['formatter', 'root', 'root_log_level', '']:
                raise ValueError('Using empty or reserved name for child logger.')
        return child_log_levels


def apply_logging_settings(logging_settings: LoggingSettings = LoggingSettings()) -> None:
    """
    Configures the python logger for the current application.

    This sets standard logging formats and attaches a single handler to the root logger. Therefore, by propagating
    messages up the logger hierarchy, all loggers automatically use the same format and formatter.
    Note: That does not work for any loggers existing before calling this method, if propagation is disabled for them.

    Log levels for the root logger and arbitrary other loggers can be set by calling with appropriate logging settings.

    When no logging settings are given, the default settings are used.

    To allow configuring log levels for individual loggers, and to make the configured log format produce meaningful
    messages, your application code should:

    * never log directly to the root logger (like ``logging.debug('message')``)

    * instead create a logger per module and log to that instance:
      | ``logger = logging.getLogger(__name__)``
      | ``logger.debug('message')``

    * not create additional log handlers or disable propagation for any loggers.

    :param logging_settings: the settings according to which logging should be configured
    """
    config = {'logging': {'formatter': logging_settings.formatter.value, 'root': logging_settings.root_log_level.value}}
    for logger_name, log_level in logging_settings.child_log_levels.items():
        config['logging'][logger_name] = log_level.name

    if config and 'logging' in config:
        logging_config_ = config['logging']

        _set_formatter(logging_config_)
        _set_root_logger(logging_config_)
        _set_loggers(logging_config_)

    logging.config.dictConfig(_logger)
    # Use a period instead of the comma before the milliseconds part
    logging.Formatter.default_msec_format = '%s.%03d'
    # Use UTC timestamps
    logging.Formatter.converter = time.gmtime
    logging.captureWarnings(True)


def _set_formatter(logging_config: dict) -> None:
    if 'formatter' in logging_config:
        formatter = logging_config['formatter']
        _logger['handlers']['console']['formatter'] = formatter
        _logger['handlers']['console']['filters'] = [formatter + '_request_id']


def _set_root_logger(logging_config: dict) -> None:
    if 'root' in logging_config:
        _logger['root']['level'] = logging_config['root']


def _set_loggers(logging_config: dict) -> None:
    loggers = [(logger, level) for logger, level in logging_config.items() if logger not in ['formatter', 'root']]
    for (logger, level) in loggers:
        if logger in _logger['loggers']:
            _logger['loggers'][logger]['level'] = level
        else:
            _logger['loggers'][logger] = {'level': level}


class StandardRequestIdFilter(logging.Filter):
    """
    Class used to include the http request id into the logged record, used with
    standard formatter.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        request_id = http_audit.get_request_id()
        # request_id is only in the log when existing
        record.request_id = '[' + request_id + '] ' if request_id else ''
        # logger and function name concatenated and truncated from the left
        record.name_with_func = (record.name + '.' + record.funcName)[-40:]
        return True


class JsonRequestIdFilter(logging.Filter):
    """
    Class used to include the http request id into the logged record, used with json formatter.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        # request_id is only added when existing
        request_id = http_audit.get_request_id()
        if request_id:
            record.request_id = request_id
            record.correlationId = request_id
        return True


class MessageContainsFilter(logging.Filter):
    """Filter log messages which contain a substring."""
    def __init__(self, substrings: Sequence[str], *args: Any, **kwargs: Any) -> None:
        """Constructor.

        :param substrings: messages which contain any of these substrings will
                           not be logged
        """
        super().__init__(*args, **kwargs)
        self._substrings = substrings

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        return not any(substring in msg for substring in self._substrings)


class LogstashJsonFormatter(jsonlogger.JsonFormatter):
    """Format JSON log entries in the same way as logstash-logback-encoder.
    https://github.com/logfellow/logstash-logback-encoder

    The JSON records have the following fields:
    - message: log message,
    - @timestamp: timestamp in ISO format, with milliseconds and time zone
    - level: 'DEBUG', 'INFO', 'WARN', 'ERROR', 'CRITICAL'
    - level_value: 10000, 20000, 30000, 40000, 50000, useful for filtering
    - logger_name: logger
    - func_name: this is not available in the logs from Spring
    - exc_info: the Spring logs have stack_trace instead
    """

    # 'message' is added by default to record.
    # 'exc_info' is transformed later when existing, cannot be easily transformed
    # to 'stack_trace'.
    _logged_fields = (
        ('asctime', '@timestamp'),
        ('threadName', 'thread_name'),
        ('levelname', 'level'),
        ('name', 'logger_name'),
        ('funcName', 'func_name'),
    )
    _log_levels = ['DEBUG', 'INFO', 'WARN', 'ERROR', 'CRITICAL']

    def add_fields(self, log_record: dict[str, Any], record: logging.LogRecord, message_dict: dict[str, Any]) -> None:
        super().add_fields(log_record, record, message_dict)
        converter = self.converter(record.created)
        log_record['@timestamp'] = time.strftime('%Y-%m-%dT%H:%M:%S.%%03d%z', converter) % record.msecs
        for src_field, field in self._logged_fields:
            value = record.__dict__.get(src_field)
            if value is not None:
                if field == 'level':
                    if value == 'WARNING':
                        value = 'WARN'
                    try:
                        log_record['level_value'] = (self._log_levels.index(value) + 1) * 10_000
                    except ValueError:
                        pass
                log_record[field] = value

