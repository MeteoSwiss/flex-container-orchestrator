import datetime
import json
import logging
import os
import sqlite3
import sys

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


def generate_flexpart_start_times(
    frt_dt: datetime.datetime, lead_time: int, tdelta: int, tfreq_f: int
) -> list[datetime.datetime]:
    """
    Generates a list of start reference times for running Flexpart simulations.

    The start times will depend on the forecast reference time and lead time that
    have been just pre-processed, the desired number of time steps for the Flexpart run,
    and the frequency of the flexpart runs.

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


def generate_forecast_label(lead_time: datetime.datetime, tfreq: int) -> str:
    """
    Returns a string in the format "{reference_time}_{step}" based on
    the given lead_time (i.e. forecast reference time + step).

    The reference_time corresponds to the latest IFS forecast run for the specified lead time.
    If the lead_time aligns with the start of an IFS simulation, it uses the previous forecast
    run with the appropriate lead time instead of the forecast at step 0.

    Args:
        lead_time (datetime.datetime): Forecasts leadtime
        tfreq (int): Frequency of IFS forecast times in hours.

    Returns:
        str: Forecast reference time (YYYYMMDDHH) followed by the lead time (HH)
        in the format "{reference_time}_{step}"
    """
    if lead_time.hour % tfreq != 0:
        frt_st = lead_time - datetime.timedelta(hours=lead_time.hour % tfreq)
        lt = lead_time.hour % tfreq
    else:
        frt_st = lead_time - datetime.timedelta(hours=tfreq)
        lt = tfreq
    return frt_st.strftime("%Y%m%d%H%M") + f"{lt:02}"


def fetch_processed_forecasts(
    conn: sqlite3.Connection, frt_s: set[datetime.datetime]
) -> set[str]:
    """
    Fetch all processed forecasts from the database for a specific reference time.

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


def define_config(start_time: datetime.datetime, end_time: datetime.datetime) -> dict:
    """
    Define input configuration for Flexpart based on provided start and end times.

    Args:
        start_time (datetime.datetime): Start time.
        end_time (datetime.datetime): End time.

    Returns:
        dict: Configuration dictionary for Flexpart.
    """
    logger.debug("Start and end time to configure Flexpart: %s and %s ", start_time, end_time)

    configuration = {
        "IBDATE": start_time.strftime("%Y%m%d"),  # Start date in YYYYMMDD format
        "IBTIME": start_time.strftime("%H"),      # Start time in HH format
        "IEDATE": end_time.strftime("%Y%m%d"),    # End date in YYYYMMDD format
        "IETIME": end_time.strftime("%H"),        # End time in HH format
        "FORECAST_DATETIME": start_time.strftime("%Y%m%d%H%M"), # Fcst ref time in YYYYMMDDHHMM format
        "RELEASE_SITE_NAME": os.environ.get("RELEASE_SITE_NAME", "BEZ") # Specify the release site in short form (ie BEZ/LEI..)
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
    start_times: list[datetime.datetime], time_settings: dict
) -> tuple[list[list[str]], list[list[datetime.datetime]], set[str]]:
    """
    Generates a list of all required forecasts for Flexpart simulations.

    Args:
        start_times (list[datetime]): List of Flexpart run start reference times.
        time_settings (dict[str, int]): Configuration containing 'tdelta' (total forecast duration in hours),
            'tincr' (increment step in hours), and 'tfreq' (frequency interval).
    Returns:
        tuple[list[list[str]], list[list[datetime]], set[str]]:
            - all_input_forecasts: A nested list where each sublist contains forecast labels
              for each Flexpart run in the format "{reference_time}_{step}".
            - all_flexpart_leadtimes: A nested list where each sublist contains datetime objects
              representing the leadtimes (reference_time + step) for each Flexpart run.
            - all_input_forecasts_set: A set of unique forecasts in the format "{reference_time}_{step}"
              required for Flexpart simulations.
    """
    time_delta = time_settings['tdelta']
    time_increment = time_settings['tincr']
    run_frequency = time_settings['tfreq']

    all_input_forecasts_set = set()
    all_input_forecasts = []
    all_flexpart_leadtimes = []

    for start_time in start_times:
        lead_times = [start_time + datetime.timedelta(hours=i) for i in range(0, time_delta, time_increment)]
        input_forecasts = [generate_forecast_label(lt, run_frequency) for lt in lead_times]

        all_input_forecasts_set.update(input_forecasts)
        all_input_forecasts.append(input_forecasts)
        all_flexpart_leadtimes.append(lead_times)

    return all_input_forecasts, all_flexpart_leadtimes, all_input_forecasts_set



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
    all_flexpart_leadtimes: list[list[datetime.datetime]],
    all_input_forecasts: list[list[str]],
    processed_forecasts: set[str],
) -> list[dict]:
    """
    Create Flexpart input configurations based on processed forecasts.

    Args:
        - all_input_forecasts: A nested list where each sublist contains forecast labels
            for each Flexpart run in the format "{reference_time}_{step}".
        - all_flexpart_leadtimes: A nested list where each sublist contains datetime objects
            representing the lead times for each Flexpart run.
        - processed_forecasts (set of str): Set of forecasts marked as processed and retrieved from the DB for
            which have the same reference times as the forecasts needed for the Flexpart simulation

    Returns:
        list of dict: List of Flexpart configuration dictionaries. If no valid
            configurations can be created, an empty list is returned.
    """
    configs = []
    for run_index, input_forecasts_for_run in enumerate(all_input_forecasts):
        if all(forecast in processed_forecasts for forecast in input_forecasts_for_run):
            config = define_config(all_flexpart_leadtimes[run_index][0], all_flexpart_leadtimes[run_index][-1])
            configs.append(config)
    return configs


def run_aggregator(date: str, time: str, step: int) -> list[dict]:
    """
    Checks if Flexpart can be launched with the processed new lead time and prepares input configurations.

    Args:
        date (str): The forecast reference date in YYYYMMDD format.
        time (str): The forecast reference time in HH format.
        step (int): The lead time in hours.

    Returns:
        list[dict]: List of configuration dictionaries for Flexpart.
    """
    time_settings = get_time_settings(CONFIG)

    DBtable = os.path.join(CONFIG.main.db.path, CONFIG.main.db.name)
    with connect_db(DBtable) as conn:
        try:
            forecast_reftime = parse_forecast_datetime(date, time)
            start_times = generate_flexpart_start_times(
                forecast_reftime,
                step,
                time_settings["tdelta"],
                time_settings["tfreq_f"]
            )

            input_forecasts, flexpart_leadtimes, input_forecasts_set = generate_forecast_times(
                start_times, time_settings
            )

            # Retrieve processed forecasts from the database
            processed_forecasts = fetch_processed_forecasts(
                conn, {strip_lead_time(forecast) for forecast in input_forecasts_set}
            )

            # Create input configurations if processed forecasts are ready
            configs = create_flexpart_configs(
                flexpart_leadtimes, input_forecasts, processed_forecasts
            )

            if not configs:
                logger.info("Not enough pre-processed forecasts to run Flexpart.")
                sys.exit(0)

            return configs

        except Exception as e:
            logger.error("An error occurred while running the aggregator: %s", e)
            raise
