from fastapi.testclient import TestClient
from datetime import datetime, timezone, timedelta
from app.config import settings


def test_book_ticket_success(client: TestClient, passenger_token: str):
    """Test booking a ticket for 2 passengers, receiving PNR and seat numbers."""
    tomorrow = (datetime.now(timezone.utc).date() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    resp = client.post(
        f"{settings.API_V1_STR}/bookings",
        headers={"Authorization": f"Bearer {passenger_token}"},
        json={
            "train_id": 1,
            "journey_date": tomorrow,
            "passengers": [
                {"name": "Aarav Sharma", "age": 28, "gender": "Male", "berth_preference": "Lower"},
                {"name": "Priya Sharma", "age": 26, "gender": "Female", "berth_preference": "Window"}
            ]
        }
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "pnr" in data
    assert data["pnr"].startswith("RC")
    assert data["total_passengers"] == 2
    assert data["booking_status"] == "CONFIRMED"
    assert data["total_fare"] == 1500.0  # 750 * 2
    assert len(data["passengers"]) == 2
    assert data["passengers"][0]["seat_number"] == "B1-1"
    assert data["passengers"][1]["seat_number"] == "B1-2"

    # Check that search shows reduced seats
    search_resp = client.get(
        f"{settings.API_V1_STR}/trains/search",
        params={"source": "NDLS", "destination": "CNB", "journey_date": tomorrow}
    )
    assert search_resp.status_code == 200
    search_data = search_resp.json()
    assert search_data[0]["available_seats"] == 48  # 50 - 2


def test_booking_history_and_pnr_lookup(client: TestClient, passenger_token: str):
    """Test retrieving booking history and looking up specific PNR."""
    tomorrow = (datetime.now(timezone.utc).date() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    # 1. Create booking
    book_resp = client.post(
        f"{settings.API_V1_STR}/bookings",
        headers={"Authorization": f"Bearer {passenger_token}"},
        json={
            "train_id": 1,
            "journey_date": tomorrow,
            "passengers": [{"name": "Aarav Sharma", "age": 28, "gender": "Male"}]
        }
    )
    pnr = book_resp.json()["pnr"]

    # 2. View my bookings
    my_resp = client.get(
        f"{settings.API_V1_STR}/bookings/my-bookings",
        headers={"Authorization": f"Bearer {passenger_token}"}
    )
    assert my_resp.status_code == 200
    my_bookings = my_resp.json()
    pnrs = [b["pnr"] for b in my_bookings]
    assert pnr in pnrs

    # 3. View booking by PNR
    pnr_resp = client.get(
        f"{settings.API_V1_STR}/bookings/{pnr}",
        headers={"Authorization": f"Bearer {passenger_token}"}
    )
    assert pnr_resp.status_code == 200
    assert pnr_resp.json()["pnr"] == pnr


def test_user_booking_isolation(client: TestClient, passenger_token: str, passenger2_token: str):
    """Test that Passenger 2 cannot view or cancel Passenger 1's booking (data isolation)."""
    tomorrow = (datetime.now(timezone.utc).date() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    # Passenger 1 books
    book_resp = client.post(
        f"{settings.API_V1_STR}/bookings",
        headers={"Authorization": f"Bearer {passenger_token}"},
        json={
            "train_id": 1,
            "journey_date": tomorrow,
            "passengers": [{"name": "Aarav Sharma", "age": 28, "gender": "Male"}]
        }
    )
    pnr = book_resp.json()["pnr"]

    # Passenger 2 tries to view Passenger 1's booking
    view_resp = client.get(
        f"{settings.API_V1_STR}/bookings/{pnr}",
        headers={"Authorization": f"Bearer {passenger2_token}"}
    )
    assert view_resp.status_code == 403
    assert "not authorized" in view_resp.json()["detail"]

    # Passenger 2 tries to cancel Passenger 1's booking
    cancel_resp = client.post(
        f"{settings.API_V1_STR}/bookings/{pnr}/cancel",
        headers={"Authorization": f"Bearer {passenger2_token}"}
    )
    assert cancel_resp.status_code == 403


def test_cancel_booking_and_seat_restoration(client: TestClient, passenger_token: str):
    """Test cancelling a booking releases seats back and prevents double cancellation."""
    tomorrow = (datetime.now(timezone.utc).date() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    # Book 3 seats
    book_resp = client.post(
        f"{settings.API_V1_STR}/bookings",
        headers={"Authorization": f"Bearer {passenger_token}"},
        json={
            "train_id": 1,
            "journey_date": tomorrow,
            "passengers": [
                {"name": "P1", "age": 30, "gender": "Male"},
                {"name": "P2", "age": 31, "gender": "Female"},
                {"name": "P3", "age": 10, "gender": "Male"}
            ]
        }
    )
    pnr = book_resp.json()["pnr"]

    # Check search seats after booking
    search1 = client.get(
        f"{settings.API_V1_STR}/trains/search",
        params={"source": "NDLS", "destination": "CNB", "journey_date": tomorrow}
    ).json()[0]["available_seats"]

    # Cancel booking
    cancel_resp = client.post(
        f"{settings.API_V1_STR}/bookings/{pnr}/cancel",
        headers={"Authorization": f"Bearer {passenger_token}"}
    )
    assert cancel_resp.status_code == 200
    cancel_data = cancel_resp.json()
    assert cancel_data["booking_status"] == "CANCELLED"
    assert cancel_data["seats_released"] == 3
    assert cancel_data["refund_status"] == "PROCESSED_SIMULATED"

    # Seats should be restored
    search2 = client.get(
        f"{settings.API_V1_STR}/trains/search",
        params={"source": "NDLS", "destination": "CNB", "journey_date": tomorrow}
    ).json()[0]["available_seats"]
    assert search2 == search1 + 3

    # Attempting to cancel again must be rejected
    repeat_cancel = client.post(
        f"{settings.API_V1_STR}/bookings/{pnr}/cancel",
        headers={"Authorization": f"Bearer {passenger_token}"}
    )
    assert repeat_cancel.status_code == 400
    assert "already been cancelled" in repeat_cancel.json()["detail"]


def test_insufficient_seats_error(client: TestClient, admin_token: str, passenger_token: str):
    """Test that requesting more seats than currently available returns 400 error."""
    # Admin sets schedule with only 1 seat available
    client.post(
        f"{settings.API_V1_STR}/admin/schedules",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "train_id": 1,
            "journey_date": "2026-12-01",
            "total_seats": 50,
            "available_seats": 1,
            "fare": 750.0
        }
    )

    # Passenger tries to book 2 seats
    resp = client.post(
        f"{settings.API_V1_STR}/bookings",
        headers={"Authorization": f"Bearer {passenger_token}"},
        json={
            "train_id": 1,
            "journey_date": "2026-12-01",
            "passengers": [
                {"name": "P1", "age": 25, "gender": "Male"},
                {"name": "P2", "age": 24, "gender": "Female"}
            ]
        }
    )
    assert resp.status_code == 400
    assert "Insufficient seats" in resp.json()["detail"]
