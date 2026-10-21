from fastapi.testclient import TestClient
from datetime import datetime, timezone, timedelta
from app.config import settings


def test_list_stations(client: TestClient):
    """Test retrieving list of railway stations."""
    resp = client.get(f"{settings.API_V1_STR}/trains/stations")
    assert resp.status_code == 200
    stations = resp.json()
    assert len(stations) >= 2
    codes = [s["code"] for s in stations]
    assert "NDLS" in codes
    assert "CNB" in codes


def test_search_trains_success(client: TestClient):
    """Test searching trains for tomorrow between NDLS and CNB."""
    tomorrow = (datetime.now(timezone.utc).date() + timedelta(days=1)).strftime("%Y-%m-%d")
    resp = client.get(
        f"{settings.API_V1_STR}/trains/search",
        params={"source": "NDLS", "destination": "CNB", "journey_date": tomorrow}
    )
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) >= 1
    t = results[0]
    assert t["train_number"] == "12004"
    assert t["source_station_code"] == "NDLS"
    assert t["destination_station_code"] == "CNB"
    assert t["available_seats"] > 0
    assert t["availability_status"] in ["AVAILABLE", "FILLING FAST"]


def test_search_trains_same_source_and_destination(client: TestClient):
    """Test that searching with identical source and destination returns 400."""
    tomorrow = (datetime.now(timezone.utc).date() + timedelta(days=1)).strftime("%Y-%m-%d")
    resp = client.get(
        f"{settings.API_V1_STR}/trains/search",
        params={"source": "NDLS", "destination": "NDLS", "journey_date": tomorrow}
    )
    assert resp.status_code == 400
    assert "cannot be the same" in resp.json()["detail"]


def test_search_trains_past_date(client: TestClient):
    """Test searching for trains in the past returns 400."""
    yesterday = (datetime.now(timezone.utc).date() - timedelta(days=1)).strftime("%Y-%m-%d")
    resp = client.get(
        f"{settings.API_V1_STR}/trains/search",
        params={"source": "NDLS", "destination": "CNB", "journey_date": yesterday}
    )
    assert resp.status_code == 400
    assert "cannot be in the past" in resp.json()["detail"]


def test_search_trains_invalid_station(client: TestClient):
    """Test searching with an unknown station code returns 404."""
    tomorrow = (datetime.now(timezone.utc).date() + timedelta(days=1)).strftime("%Y-%m-%d")
    resp = client.get(
        f"{settings.API_V1_STR}/trains/search",
        params={"source": "INVALID", "destination": "CNB", "journey_date": tomorrow}
    )
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"]
