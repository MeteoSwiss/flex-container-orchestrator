import logging

import pytest

from flex_container_orchestrator.services.flexpart_service import run_command


# Mock logging
@pytest.fixture(autouse=True)
def mock_logging(caplog):
    with caplog.at_level(logging.INFO):
        yield caplog


def test_run_command_success():
    command = ["echo", "Hello"]
    result = run_command(command, capture_output=True)
    assert result == b"Hello"


def test_run_command_failure():
    command = ["false"]  # This command will fail
    with pytest.raises(SystemExit):
        run_command(command)
