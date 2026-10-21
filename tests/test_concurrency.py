from fastapi.testclient import TestClient
from concurrent.futures import ThreadPoolExecutor
from app.config import settings


def test_concurrent_booking_prevents_overbooking(client: TestClient, admin_token: str, passenger_token: str):
    """
    Test high-concurrency race condition:
    Set available seats to exactly 2.
    Launch 6 concurrent booking requests each requesting 1 seat.
    Verify that exactly 2 succeed and 4 are cleanly rejected with 400 Insufficient seats.
    """
    journey_date = "2026-12-25"
    
    # 1. Admin configures exactly 2 available seats
    setup_resp = client.post(
        f"{settings.API_V1_STR}/admin/schedules",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "train_id": 1,
            "journey_date": journey_date,
            "total_seats": 2,
            "available_seats": 2,
            "fare": 500.0
        }
    )
    assert setup_resp.status_code == 201

    def make_booking(idx: int):
        return client.post(
            f"{settings.API_V1_STR}/bookings",
            headers={"Authorization": f"Bearer {passenger_token}"},
            json={
                "train_id": 1,
                "journey_date": journey_date,
                "passengers": [{"name": f"Passenger {idx}", "age": 25 + idx, "gender": "Other"}]
            }
        )

    # Execute 6 concurrent booking requests
    with ThreadPoolExecutor(max_workers=6) as executor:
        responses = list(executor.map(make_booking, range(6)))

    status_codes = [r.status_code for r in responses]
    success_count = status_codes.count(201)
    failed_count = status_codes.count(400)

    # Exactly 2 should succeed, 4 should fail
    assert success_count == 2, f"Expected 2 successes, got {success_count}. Codes: {status_codes}"
    assert failed_count == 4, f"Expected 4 failures, got {failed_count}. Codes: {status_codes}"

    # Search should now report 0 available seats and status "SOLD OUT"
    search_resp = client.get(
        f"{settings.API_V1_STR}/trains/search",
        params={"source": "NDLS", "destination": "CNB", "journey_date": journey_date}
    )
    assert search_resp.status_code == 200
    search_item = search_resp.json()[0]
    assert search_item["available_seats"] == 0
    assert search_item["availability_status"] == "SOLD OUT"
