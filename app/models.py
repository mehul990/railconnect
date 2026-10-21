from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime, timezone


def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True, max_length=255)
    full_name: str = Field(max_length=255)
    hashed_password: str = Field(max_length=255)
    role: str = Field(default="passenger", max_length=50)  # "admin" or "passenger"
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=get_utc_now)


class RevokedToken(SQLModel, table=True):
    __tablename__ = "revoked_tokens"

    id: Optional[int] = Field(default=None, primary_key=True)
    token_identifier: str = Field(unique=True, index=True, max_length=512)
    revoked_at: datetime = Field(default_factory=get_utc_now)
    expires_at: datetime


class PasswordResetToken(SQLModel, table=True):
    __tablename__ = "password_reset_tokens"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    token: str = Field(unique=True, index=True, max_length=255)
    is_used: bool = Field(default=False)
    expires_at: datetime
    created_at: datetime = Field(default_factory=get_utc_now)


class Station(SQLModel, table=True):
    __tablename__ = "stations"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(unique=True, index=True, max_length=10)  # e.g., NDLS, CNB
    name: str = Field(max_length=255)  # e.g., New Delhi Railway Station
    city: str = Field(max_length=255)  # e.g., New Delhi
    state: Optional[str] = Field(default=None, max_length=255)


class Train(SQLModel, table=True):
    __tablename__ = "trains"

    id: Optional[int] = Field(default=None, primary_key=True)
    train_number: str = Field(unique=True, index=True, max_length=20)  # e.g., 12004
    train_name: str = Field(max_length=255)  # e.g., Lucknow Shatabdi
    source_station_code: str = Field(index=True, max_length=10)  # e.g., NDLS
    destination_station_code: str = Field(index=True, max_length=10)  # e.g., CNB
    departure_time: str = Field(max_length=10)  # e.g., 06:10
    arrival_time: str = Field(max_length=10)  # e.g., 11:20
    travel_duration: str = Field(max_length=20)  # e.g., 5h 10m
    total_seats: int = Field(default=120, ge=1)
    base_fare: float = Field(default=750.0, ge=0.0)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=get_utc_now)


class TrainRouteStop(SQLModel, table=True):
    __tablename__ = "train_route_stops"

    id: Optional[int] = Field(default=None, primary_key=True)
    train_id: int = Field(foreign_key="trains.id", index=True)
    station_code: str = Field(index=True, max_length=10)
    stop_sequence: int = Field(ge=1)  # 1, 2, 3...
    arrival_time: Optional[str] = Field(default=None, max_length=10)
    departure_time: Optional[str] = Field(default=None, max_length=10)
    distance_km: int = Field(default=0, ge=0)


class TrainSchedule(SQLModel, table=True):
    __tablename__ = "train_schedules"

    id: Optional[int] = Field(default=None, primary_key=True)
    train_id: int = Field(foreign_key="trains.id", index=True)
    journey_date: str = Field(index=True, max_length=10)  # Format: YYYY-MM-DD
    total_seats: int = Field(ge=1)
    available_seats: int = Field(ge=0)
    fare: float = Field(ge=0.0)
    is_cancelled: bool = Field(default=False)


class Booking(SQLModel, table=True):
    __tablename__ = "bookings"

    id: Optional[int] = Field(default=None, primary_key=True)
    pnr: str = Field(unique=True, index=True, max_length=20)
    user_id: int = Field(foreign_key="users.id", index=True)
    train_id: int = Field(foreign_key="trains.id", index=True)
    train_number: str = Field(max_length=20)
    train_name: str = Field(max_length=255)
    source_station: str = Field(max_length=50)
    destination_station: str = Field(max_length=50)
    journey_date: str = Field(index=True, max_length=10)  # YYYY-MM-DD
    total_passengers: int = Field(ge=1)
    total_fare: float = Field(ge=0.0)
    booking_status: str = Field(default="CONFIRMED", max_length=20)  # CONFIRMED, CANCELLED
    payment_status: str = Field(default="COMPLETED", max_length=20)  # Simulated
    created_at: datetime = Field(default_factory=get_utc_now)
    cancelled_at: Optional[datetime] = Field(default=None)


class Passenger(SQLModel, table=True):
    __tablename__ = "passengers"

    id: Optional[int] = Field(default=None, primary_key=True)
    booking_id: int = Field(foreign_key="bookings.id", index=True)
    name: str = Field(max_length=255)
    age: int = Field(ge=1, le=120)
    gender: str = Field(max_length=20)
    seat_number: str = Field(max_length=20)
    berth_preference: Optional[str] = Field(default="None", max_length=50)
