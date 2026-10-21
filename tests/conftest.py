import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, create_engine, Session
from sqlmodel.pool import StaticPool
from datetime import datetime, timezone, timedelta

from app.main import app
from app.database import get_session
from app.models import User, Station, Train, TrainSchedule
from app.security import hash_password
from app.config import settings


from pathlib import Path


@pytest.fixture(name="engine_fixture")
def engine_fixture(tmp_path: Path):
    """Create an isolated file-backed SQLite database for testing and concurrency."""
    db_file = tmp_path / "test_railconnect.db"
    test_engine = create_engine(
        f"sqlite:///{db_file}",
        connect_args={"check_same_thread": False, "timeout": 30}
    )
    SQLModel.metadata.create_all(test_engine)
    with Session(test_engine) as session:
        # Pre-seed Admin
        admin = User(
            email="admin@railconnect.com",
            full_name="Railway Super Admin",
            hashed_password=hash_password("Admin@ChangeMe123"),
            role="admin",
            is_active=True
        )
        session.add(admin)

        # Pre-seed Passenger 1
        passenger1 = User(
            email="aarav@example.com",
            full_name="Aarav Sharma",
            hashed_password=hash_password("Password@123"),
            role="passenger",
            is_active=True
        )
        session.add(passenger1)

        # Pre-seed Passenger 2 (for isolation testing)
        passenger2 = User(
            email="rohit@example.com",
            full_name="Rohit Verma",
            hashed_password=hash_password("Password@123"),
            role="passenger",
            is_active=True
        )
        session.add(passenger2)

        # Stations
        ndls = Station(code="NDLS", name="New Delhi Railway Station", city="New Delhi", state="Delhi")
        cnb = Station(code="CNB", name="Kanpur Central", city="Kanpur", state="Uttar Pradesh")
        session.add(ndls)
        session.add(cnb)

        # Train
        train = Train(
            train_number="12004",
            train_name="New Delhi - Kanpur Shatabdi Express",
            source_station_code="NDLS",
            destination_station_code="CNB",
            departure_time="06:10",
            arrival_time="11:20",
            travel_duration="5h 10m",
            total_seats=50,
            base_fare=750.0,
            is_active=True
        )
        session.add(train)
        session.commit()
        session.refresh(train)

        # Future schedule
        tomorrow = (datetime.now(timezone.utc).date() + timedelta(days=1)).strftime("%Y-%m-%d")
        schedule = TrainSchedule(
            train_id=train.id,
            journey_date=tomorrow,
            total_seats=50,
            available_seats=50,
            fare=750.0,
            is_cancelled=False
        )
        session.add(schedule)
        session.commit()

    return test_engine


@pytest.fixture(name="client")
def client_fixture(engine_fixture):
    """TestClient that uses the isolated in-memory test database with thread-safe sessions."""
    def get_session_override():
        with Session(engine_fixture) as session:
            yield session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture(name="admin_token")
def admin_token_fixture(client: TestClient):
    """Return an active admin JWT access token."""
    resp = client.post(
        f"{settings.API_V1_STR}/auth/login",
        json={"email": "admin@railconnect.com", "password": "Admin@ChangeMe123"}
    )
    return resp.json()["access_token"]


@pytest.fixture(name="passenger_token")
def passenger_token_fixture(client: TestClient):
    """Return an active passenger JWT access token for Aarav."""
    resp = client.post(
        f"{settings.API_V1_STR}/auth/login",
        json={"email": "aarav@example.com", "password": "Password@123"}
    )
    return resp.json()["access_token"]


@pytest.fixture(name="passenger2_token")
def passenger2_token_fixture(client: TestClient):
    """Return an active passenger JWT access token for Rohit."""
    resp = client.post(
        f"{settings.API_V1_STR}/auth/login",
        json={"email": "rohit@example.com", "password": "Password@123"}
    )
    return resp.json()["access_token"]
