#!/usr/bin/env python3

import argparse
import datetime
import json
import logging
import sqlite3
import subprocess
import sys
import os
import yaml

import boto3
from botocore.exceptions import ClientError


def parse_arguments():
    """
    Parse command-line arguments.

    Returns:
        argparse.Namespace: Parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description="Launch Flexpart after processing checks."
    )
    parser.add_argument("--date", required=True, help="Date in YYYYMMDD format")
    parser.add_argument("--time", required=True, help="Time in HH format")
    parser.add_argument(
        "--step", required=True, help="Step identifier (lead time in hours)"
    )
    parser.add_argument("--db_path", required=True, help="Path to the SQLite database")
    return parser.parse_args()


def connect_db(db_path):
    """
    Establish a connection to the SQLite database.

    Args:
        db_path (str): Path to the SQLite database.

    Returns:
        sqlite3.Connection: SQLite connection object.
    """
    try:
        conn = sqlite3.connect(db_path)
        logging.info(f"Connected to SQLite database at {db_path}.")
        return conn
    except sqlite3.Error as e:
        logging.error(f"SQLite connection error: {e}")
        sys.exit(1)


def is_row_processed(conn, forecast_ref_time, step):
    """
    Check if a specific row in the database has been processed.

    Args:
        conn (sqlite3.Connection): SQLite connection object.
        forecast_ref_time (str): Forecast reference time in YYYYMMDDHHMM format.
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
        else:
            logging.info(
                f"No row found for forecast_ref_time={forecast_ref_time} and step={step}."
            )
            return False
    except sqlite3.Error as e:
        logging.error(f"SQLite query error: {e}")
        sys.exit(1)


def generate_flexpart_start_times(frt_dt, lead_time, tdelta, tfreq_f):
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
    max_start_time = lt_dt.replace(hour=(lt_dt.hour - (lt_dt.hour % tfreq_f)))

    list_start_times = []
    current_start = min_start_time
    delta = datetime.timedelta(hours=tfreq_f)
    while current_start <= max_start_time:
        list_start_times.append(current_start)
        current_start += delta

    return list_start_times


def convert_time_to_frt(time, tfreq):
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


def fetch_processed_items(conn, frt_s):
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
            for item in items_f:
                if item[0]:  # processed == True
                    processed_items.add(frt + f"{int(item[1]):02}")
    except sqlite3.Error as e:
        logging.error(f"SQLite query error while fetching processed items: {e}")
        sys.exit(1)
    return processed_items


def define_config(st: datetime.datetime, et: datetime.datetime):

    logging.info(f'Start and end time to configure Flexpart: {st} and {et} ')

    configuration = {
        'IBDATE': st.strftime("%Y%m%d"),
        'IBTIME': st.strftime("%H"),
        'IEDATE': et.strftime("%Y%m%d"),
        'IETIME': et.strftime("%H")
    }

    logging.info(f'Configuration to run Flexpart: {json.dumps(configuration)}')

    return configuration


def main():
    args = parse_arguments()

    DATE = args.date
    TIME = args.time
    STEP = args.step
    DB_PATH = args.db_path

    # Constants
    TINCR = 1  # How many hours between time steps
    TDELTA = 6  # Number of timesteps to run Flexpart with (temporarily set to 6 timesteps but operational config is 90)
    TFREQ_F = 6  # Frequency of Flexpart runs in hours
    TFREQ = 6  # Frequency of IFS forecast times in hours

    # Connect to the database
    conn = connect_db(DB_PATH)

    frt_dt = datetime.datetime.strptime(f"{DATE}{int(TIME):02d}00", "%Y%m%d%H%M")

    # Check if the specific row is processed
    if not is_row_processed(conn, frt_dt, STEP):
        logging.info("File processing incomplete. Exiting before launching Flexpart.")
        conn.close()
        sys.exit(0)

    lead_time = int(STEP)
    list_start_times = generate_flexpart_start_times(frt_dt, lead_time, TDELTA, TFREQ_F)

    logging.info(f"Generated {len(list_start_times)} Flexpart start times.")

    all_steps = set()
    all_list_ltf = []
    all_list_lt = []

    for start_time in list_start_times:
        logging.info(f"Start time: {start_time}")
        list_ltf = []
        list_lt = []
        for i in range(0, TDELTA, TINCR):
            time = start_time + datetime.timedelta(hours=i)
            forecast = convert_time_to_frt(time, TFREQ)
            list_ltf.append(forecast)
            list_lt.append(time)
            all_steps.add(forecast)
        all_list_ltf.append(list_ltf)
        all_list_lt.append(list_lt)

    # Generate forecast ref time by stripping the last two characters (lead time)
    frt_s = {
        datetime.datetime.strptime(forecast[:-2], "%Y%m%d%H%M")
        for forecast in all_steps
    }

    # Fetch processed items from the database
    processed_items = fetch_processed_items(conn, frt_s)

    # Iterate over all_list_ltf to determine if Flexpart should be launched
    configs = []
    for i, flexpart_run in enumerate(all_list_ltf):
        tstart = all_list_lt[i][0]
        tend = all_list_lt[i][-1]
        if all(item in processed_items for item in flexpart_run):
            config = define_config(tstart, tend)
            configs.append(config)

    print(json.dumps(configs))

    # Close the database connection
    conn.close()


if __name__ == "__main__":
    main()
