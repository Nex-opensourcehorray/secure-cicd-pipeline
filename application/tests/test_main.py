"""API behavior tests for the secure CI/CD demo service."""

import importlib

import pytest
from fastapi.testclient import TestClient

from app import main as main_module


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Create a client with the application's documented default settings."""
    monkeypatch.delenv("APP_NAME", raising=False)
    monkeypatch.delenv("APP_VERSION", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)

    default_main = importlib.reload(main_module)
    with TestClient(default_main.app) as test_client:
        yield test_client


def test_root_endpoint(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "service": "secure-cicd-demo",
        "status": "running",
    }


def test_health_endpoint(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_version_endpoint(client: TestClient) -> None:
    response = client.get("/version")

    assert response.status_code == 200
    assert response.json() == {
        "version": "0.1.0",
        "environment": "development",
    }


def test_environment_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_NAME", "secure-cicd-test")
    monkeypatch.setenv("APP_VERSION", "0.1.0-test")
    monkeypatch.setenv("APP_ENV", "test")

    configured_main = importlib.reload(main_module)
    with TestClient(configured_main.app) as configured_client:
        root_response = configured_client.get("/")
        version_response = configured_client.get("/version")

    assert root_response.status_code == 200
    assert root_response.json()["service"] == "secure-cicd-test"
    assert version_response.status_code == 200
    assert version_response.json() == {
        "version": "0.1.0-test",
        "environment": "test",
    }


def test_unknown_route_returns_404(client: TestClient) -> None:
    response = client.get("/does-not-exist")

    assert response.status_code == 404
