import datetime
import json
import logging
import sqlite3
import sys
from typing import List, Set, Tuple

from flex_container_orchestrator import CONFIG

logger = logging.getLogger(__name__)

def connect_db(db_path: str) -> sqlite3.Connection:
    """
    Establish a connection to the SQLite database.

    Args:
        db_path (str): Path to the SQLite database.

    Returns:
        sqlite3.Connection: SQLite connection object.
    """
    try:
        conn = sqlite3.connect(db_path)
        logger.info("Connected to SQLite database at %s.", db_path)
        return conn
    except sqlite3.Error as e:
        logger.error("SQLite connection error: %s", e)
        sys.exit(1)


def is_lead_time_processed(
    conn: sqlite3.Connection, forecast_ref_time: datetime.datetime, step: str
) -> bool:
    """
    Check if a specific row in the database has been processed.

    Args:
        conn (sqlite3.Connection): SQLite connection object.
        forecast_ref_time (datetime): Forecast reference time
        step (str): Step identifier.

    Returns:
        bool: True if processed, False otherwise.
    """
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT processed FROM uploaded
            WHERE forecast_ref_time = ? AND step = ?
        """,
            (forecast_ref_time, step),
        )
        result = cursor.fetchone()
        if result:
            return result[0] == 1
        logger.info(
            "No row found for forecast_ref_time=%s and step=%s.",
            forecast_ref_time,
            step,
        )
        return False
    except sqlite3.Error as e:
        logger.error("SQLite query error: %s", e)
        sys.exit(1)


def generate_flexpart_start_times(
    frt_dt: datetime.datetime, lead_time: int, tdelta: int, tfreq_f: int
) -> List[datetime.datetime]:
    """
    Generate a list of Flexpart run start times.

    Args:
        frt_dt (datetime.datetime): Forecast reference datetime.
        lead_time (int): Lead time in hours.
        tdelta (int): Number of timesteps to run Flexpart with.
        tfreq_f (int): Frequency of Flexpart runs in hours.

    Returns:
        list of datetime.datetime: List of Flexpart run start times.
    """
    lt_dt = frt_dt + datetime.timedelta(hours=lead_time)
    lt_tmp = lt_dt - datetime.timedelta(hours=tdelta)
    min_start_time = lt_tmp + datetime.timedelta(
        hours=tfreq_f - (lt_tmp.hour % tfreq_f)
    )
    max_start_time = lt_dt.replace(hour=lt_dt.hour - (lt_dt.hour % tfreq_f))

    list_start_times = []
    current_start = min_start_time
    delta = datetime.timedelta(hours=tfreq_f)
    while current_start <= max_start_time:
        list_start_times.append(current_start)
        current_start += delta

    return list_start_times


def convert_time_to_frt(time: datetime.datetime, tfreq: int) -> str:
    """
    Convert time object into IFS forecast objects to use.

    Args:
        time (datetime.datetime): Datetime object.
        tfreq (int): Frequency of IFS forecast times in hours.

    Returns:
        str: Forecast reference time (YYYYMMDDHH) followed by the lead time (HH)
    """
    if time.hour % tfreq != 0:
        frt_st = time - datetime.timedelta(hours=time.hour % tfreq)
        lt = time.hour % tfreq
    else:
        frt_st = time - datetime.timedelta(hours=tfreq)
        lt = tfreq
    return frt_st.strftime("%Y%m%d%H%M") + f"{lt:02}"


def fetch_processed_items(
    conn: sqlite3.Connection, frt_s: Set[datetime.datetime]
) -> Set[str]:
    """
    Fetch all processed items from the database.

    Args:
        conn (sqlite3.Connection): SQLite connection object.
        frt_s (set of str): Set of forecast reference times (stripped of last two characters).

    Returns:
        set of str: Set of processed item identifiers.
    """
    processed_items = set()
    try:
        cursor = conn.cursor()
        for frt in frt_s:
            cursor.execute(
                """
                SELECT processed, step FROM uploaded
                WHERE forecast_ref_time = ?
            """,
                (frt,),
            )
            items_f = cursor.fetchall()
             for processed, step in items_f:
                if processed:
                    frt_str = (
                        frt.strftime("%Y%m%d%H%M")
                        if isinstance(frt, datetime.datetime)
                        else str(frt)
                    )
                    processed_items.add(frt_str + f"{int(step):02}")
    except sqlite3.Error as e:
        logger.error("SQLite query error while fetching processed items: %s", e)
        sys.exit(1)
    return processed_items


def define_config(st: datetime.datetime, et: datetime.datetime) -> dict:
    """
    Define configuration for Flexpart.

    Args:
        st (datetime.datetime): Start time.
        et (datetime.datetime): End time.

    Returns:
        dict: Configuration dictionary for Flexpart.
    """
    logger.info("Start and end time to configure Flexpart: %s and %s ", st, et)

    configuration = {
        "IBDATE": st.strftime("%Y%m%d"),
        "IBTIME": st.strftime("%H"),
        "IEDATE": et.strftime("%Y%m%d"),
        "IETIME": et.strftime("%H"),
    }

    logger.debug("Configuration to run Flexpart: %s", json.dumps(configuration))

    return configuration


# mypy: ignore-errors
def get_time_settings(config) -> dict:
    """
    Retrieve time settings from config.

    Args:
        config: Configuration object.

    Returns:
        dict: Dictionary with time settings.
    """
    return {
        "tincr": config.main.time_settings.tincr,
        "tdelta": config.main.time_settings.tdelta,
        "tfreq_f": config.main.time_settings.tfreq_f,
        "tfreq": config.main.time_settings.tfreq,
    }


def parse_forecast_datetime(date_str: str, time_str: str) -> datetime.datetime:
    """
    Parse forecast date and time strings into a datetime object.

    Args:
        date_str (str): Date in YYYYMMDD format.
        time_str (str): Time in HH format.

    Returns:
        datetime.datetime: Parsed datetime object.
    """
    return datetime.datetime.strptime(f"{date_str}{int(time_str):02d}00", "%Y%m%d%H%M")


def generate_forecast_times(
    list_start_times: List[datetime.datetime], time_settings: dict
) -> Tuple[List[List[str]], List[List[datetime.datetime]], Set[str]]:
    """
    Generate forecast times for Flexpart runs.

    Args:
        list_start_times (list of datetime.datetime): List of Flexpart run start times.
        time_settings (dict): Time settings dictionary.

    Returns:
        tuple: Tuple containing lists of forecast times, lead times, and all steps.
    """
    all_steps = set()
    all_list_ltf = []
    all_list_lt = []
    for start_time in list_start_times:
        logger.info("Start time: %s", start_time)
        list_ltf = []
        list_lt = []
        for i in range(0, time_settings["tdelta"], time_settings["tincr"]):
            time = start_time + datetime.timedelta(hours=i)
            forecast = convert_time_to_frt(time, time_settings["tfreq"])
            list_ltf.append(forecast)
            list_lt.append(time)
            all_steps.add(forecast)
        all_list_ltf.append(list_ltf)
        all_list_lt.append(list_lt)
    return all_list_ltf, all_list_lt, all_steps


def strip_lead_time(forecast: str) -> datetime.datetime:
    """
    Strip lead time from forecast string.

    Args:
        forecast (str): Forecast reference time with lead time.

    Returns:
        datetime.datetime: Forecast datetime without lead time.
    """
    return datetime.datetime.strptime(forecast[:-2], "%Y%m%d%H%M")


def create_flexpart_configs(
    all_list_lt: List[List[datetime.datetime]],
    all_list_ltf: List[List[str]],
    processed_items: Set[str],
) -> List[dict]:
    """
    Create Flexpart configurations based on processed items.

    Args:
        all_list_lt (list of list of datetime.datetime): List of lead times.
        all_list_ltf (list of list of str): List of forecast reference times with lead times.
        processed_items (set of str): Set of processed item identifiers.

    Returns:
        list of dict: List of Flexpart configuration dictionaries.
    """
    configs = []
    for i, flexpart_run in enumerate(all_list_ltf):
        if all(item in processed_items for item in flexpart_run):
            config = define_config(all_list_lt[i][0], all_list_lt[i][-1])
            configs.append(config)
    return configs


def run_aggregator(date: str, time: str, step: int, db_path: str) -> List[dict]:
    """
    Run the aggregator function with the provided arguments.

    Args:
        date (str): Date in YYYYMMDD format.
        time (str): Time in HH format.
        step (int): Step identifier (lead time in hours).
        db_path (str): Path to the SQLite database.

    Returns:
        List[dict]: List of configuration dictionaries for Flexpart.
    """
    time_settings = get_time_settings(CONFIG)
    conn = connect_db(db_path)
    frt_dt = parse_forecast_datetime(date, time)

    if not is_lead_time_processed(conn, frt_dt, step):
        logger.info("File processing incomplete. Exiting before launching Flexpart.")
        conn.close()
        sys.exit(0)

    list_start_times = generate_flexpart_start_times(
        frt_dt,
        step,
        time_settings["tdelta"],
        time_settings["tfreq_f"],
    )
    all_list_ltf, all_list_lt, all_steps = generate_forecast_times(
        list_start_times, time_settings
    )

    frt_set = {strip_lead_time(forecast) for forecast in all_steps}
    processed_items = fetch_processed_items(conn, frt_set)

    configs = create_flexpart_configs(all_list_lt, all_list_ltf, processed_items)
    conn.close()

    return configs
