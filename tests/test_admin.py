from fastapi.testclient import TestClient
from app.config import settings


def test_passenger_cannot_access_admin_endpoints(client: TestClient, passenger_token: str):
    """Test that standard passengers receive 403 Forbidden on admin APIs."""
    resp = client.post(
        f"{settings.API_V1_STR}/admin/stations",
        headers={"Authorization": f"Bearer {passenger_token}"},
        json={"code": "LKO", "name": "Lucknow", "city": "Lucknow"}
    )
    assert resp.status_code == 403
    assert "Administrator access required" in resp.json()["detail"]


def test_admin_create_station(client: TestClient, admin_token: str):
    """Test admin creating a new station."""
    resp = client.post(
        f"{settings.API_V1_STR}/admin/stations",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"code": "LKO", "name": "Lucknow Charbagh", "city": "Lucknow", "state": "UP"}
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["code"] == "LKO"
    assert data["name"] == "Lucknow Charbagh"


def test_admin_create_train(client: TestClient, admin_token: str):
    """Test admin adding a new train with timings, seats, and fare."""
    resp = client.post(
        f"{settings.API_V1_STR}/admin/trains",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "train_number": "12452",
            "train_name": "Shram Shakti Express",
            "source_station_code": "NDLS",
            "destination_station_code": "CNB",
            "departure_time": "23:55",
            "arrival_time": "06:00",
            "travel_duration": "6h 05m",
            "total_seats": 150,
            "base_fare": 480.0
        }
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["train_number"] == "12452"
    assert data["total_seats"] == 150
    assert data["base_fare"] == 480.0
    assert data["is_active"] is True


def test_admin_update_and_deactivate_train(client: TestClient, admin_token: str):
    """Test admin updating train metadata and deactivating/activating."""
    # 1. Update train fare and duration
    resp = client.put(
        f"{settings.API_V1_STR}/admin/trains/1",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"base_fare": 850.0, "travel_duration": "4h 55m"}
    )
    assert resp.status_code == 200
    assert resp.json()["base_fare"] == 850.0

    # 2. Deactivate train
    resp_deact = client.patch(
        f"{settings.API_V1_STR}/admin/trains/1/deactivate",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp_deact.status_code == 200
    assert resp_deact.json()["is_active"] is False

    # 3. Reactivate train
    resp_act = client.patch(
        f"{settings.API_V1_STR}/admin/trains/1/activate",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp_act.status_code == 200
    assert resp_act.json()["is_active"] is True


def test_admin_manage_schedules(client: TestClient, admin_token: str):
    """Test admin setting seat inventory and fares for specific journey dates."""
    resp = client.post(
        f"{settings.API_V1_STR}/admin/schedules",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "train_id": 1,
            "journey_date": "2026-11-15",
            "total_seats": 80,
            "available_seats": 80,
            "fare": 900.0
        }
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["total_seats"] == 80
    assert data["fare"] == 900.0
