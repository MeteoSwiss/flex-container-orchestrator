import datetime
from unittest.mock import MagicMock, patch

import pytest

from flex_container_orchestrator.domain.aggregator_flexpart import (
    convert_time_to_frt, define_config, fetch_processed_items,
    generate_flexpart_start_times, is_row_processed)


@pytest.mark.parametrize(
    "fetchone_return, expected_result",
    [
        ((1,), True),  # Case where row is processed
        ((0,), False),  # Case where row is not processed
    ],
)
def test_is_row_processed(fetchone_return, expected_result):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_conn.cursor.return_value = mock_cursor

    mock_cursor.execute.return_value = mock_cursor  # execute returns the cursor itself
    mock_cursor.fetchone.return_value = (
        fetchone_return  # fetchone returns the tuple for testing
    )

    result = is_row_processed(mock_conn, datetime.datetime(2023, 10, 22, 6, 0), "12")

    assert result == expected_result


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
def test_convert_time_to_frt(time, tfreq, expected):
    result = convert_time_to_frt(time, tfreq)
    assert result == expected


@patch("sqlite3.connect")
def test_fetch_processed_items(mock_connect):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchall.return_value = [(True, "12"), (False, "24")]
    frt_s = {datetime.datetime(2023, 10, 22, 6, 0)}
    result = fetch_processed_items(mock_conn, frt_s)
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
    }
    assert result == expected_config
