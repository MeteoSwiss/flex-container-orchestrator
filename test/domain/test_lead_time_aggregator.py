import datetime
from unittest.mock import MagicMock, patch

import pytest

from flex_container_orchestrator.domain.lead_time_aggregator import (
    generate_forecast_label, define_config, fetch_processed_forecasts,
    generate_flexpart_start_times)


@pytest.mark.parametrize(
    "frt_dt, lead_time, tdelta, tfreq_f, expected",
    [
        (
            datetime.datetime(2023, 10, 22, 6, 0),
            12,
            24,
            6,
            [
                datetime.datetime(2023, 10, 22, 0, 0),
                datetime.datetime(2023, 10, 22, 6, 0),
                datetime.datetime(2023, 10, 22, 12, 0),
                datetime.datetime(2023, 10, 22, 18, 0),
            ],
        ),
        (
            datetime.datetime(2023, 10, 22, 6, 0),
            6,
            12,
            3,
            [
                datetime.datetime(2023, 10, 22, 3, 0),
                datetime.datetime(2023, 10, 22, 6, 0),
                datetime.datetime(2023, 10, 22, 9, 0),
                datetime.datetime(2023, 10, 22, 12, 0),
            ],
        ),
    ],
)
def test_generate_flexpart_start_times(frt_dt, lead_time, tdelta, tfreq_f, expected):
    result = generate_flexpart_start_times(frt_dt, lead_time, tdelta, tfreq_f)
    assert result == expected


@pytest.mark.parametrize(
    "time, tfreq, expected",
    [
        (datetime.datetime(2023, 10, 22, 10, 0), 6, "20231022060004"),
        (datetime.datetime(2023, 10, 22, 12, 0), 6, "20231022060006"),
    ],
)
def test_generate_forecast_label(time, tfreq, expected):
    result = generate_forecast_label(time, tfreq)
    assert result == expected


@patch("sqlite3.connect")
def test_fetch_processed_forecasts(mock_connect):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchall.return_value = [(True, "12"), (False, "24")]
    frt_s = {datetime.datetime(2023, 10, 22, 6, 0)}
    result = fetch_processed_forecasts(mock_conn, frt_s)
    assert result == {"20231022060012"}


def test_define_config():
    st = datetime.datetime(2023, 10, 22, 6, 0)
    et = datetime.datetime(2023, 10, 22, 18, 0)
    result = define_config(st, et)
    expected_config = {
        "IBDATE": "20231022",
        "IBTIME": "06",
        "IEDATE": "20231022",
        "IETIME": "18",
        "FORECAST_DATETIME": "202310220600",
        "RELEASE_SITE_NAME": "BEZ"
    }
    assert result == expected_config
