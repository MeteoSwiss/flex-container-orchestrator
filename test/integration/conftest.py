import pytest

from fastapi.testclient import TestClient

from flex_container_orchestrator.main import app


@pytest.fixture
def test_client():
    with TestClient(app) as client:
        yield client
