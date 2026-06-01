"""Tests for health and root endpoints."""

import pytest
from fastapi.testclient import TestClient
from marginalia.main import app

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "marginalia"


def test_root_returns_message():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "marginalia" in data["message"].lower()
