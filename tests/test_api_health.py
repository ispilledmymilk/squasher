"""Smoke tests for FastAPI app (no auth)."""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("API_SECRET_KEY", "")
    monkeypatch.setenv("ENV", "development")
    from api.main import app

    return TestClient(app)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json().get("status") == "healthy"


def test_root(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.json().get("service") == "codedecay-qa"
