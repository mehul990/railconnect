from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict
from typing import Optional, List
from datetime import datetime, date
import re


# --- Auth & User Schemas ---

class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, description="Password must be at least 6 characters")
    full_name: str = Field(min_length=2, max_length=100)
    role: Optional[str] = Field(default="passenger", description="'passenger' or 'admin'")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: Optional[str]) -> str:
        if v and v.lower() not in ["passenger", "admin"]:
            raise ValueError("Role must be either 'passenger' or 'admin'")
        return (v or "passenger").lower()


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user_id: int
    email: str


class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    message: str
    dev_reset_token: Optional[str] = None
    expires_in_minutes: int


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=6, description="New password must be at least 6 characters")


class MessageResponse(BaseModel):
    message: str


# --- Station Schemas ---

class StationCreate(BaseModel):
    code: str = Field(min_length=2, max_length=10, description="Station code (e.g., NDLS)")
    name: str = Field(min_length=2, max_length=100)
    city: str = Field(min_length=2, max_length=100)
    state: Optional[str] = None

    @field_validator("code")
    @classmethod
    def uppercase_code(cls, v: str) -> str:
        return v.strip().upper()


class StationOut(BaseModel):
    id: int
    code: str
    name: str
    city: str
    state: Optional[str]

    model_config = ConfigDict(from_attributes=True)


# --- Train Schemas ---

class TrainCreate(BaseModel):
    train_number: str = Field(min_length=3, max_length=20, description="Train Number (e.g. 12004)")
    train_name: str = Field(min_length=3, max_length=100)
    source_station_code: str = Field(min_length=2, max_length=10)
    destination_station_code: str = Field(min_length=2, max_length=10)
    departure_time: str = Field(pattern=r"^\d{2}:\d{2}$", description="Departure time in HH:MM format")
    arrival_time: str = Field(pattern=r"^\d{2}:\d{2}$", description="Arrival time in HH:MM format")
    travel_duration: str = Field(description="e.g. 5h 10m")
    total_seats: int = Field(default=120, ge=1, le=2000)
    base_fare: float = Field(default=750.0, ge=0.0)

    @field_validator("source_station_code", "destination_station_code")
    @classmethod
    def uppercase_station_code(cls, v: str) -> str:
        return v.strip().upper()


class TrainUpdate(BaseModel):
    train_name: Optional[str] = None
    departure_time: Optional[str] = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    arrival_time: Optional[str] = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    travel_duration: Optional[str] = None
    total_seats: Optional[int] = Field(default=None, ge=1)
    base_fare: Optional[float] = Field(default=None, ge=0.0)
    is_active: Optional[bool] = None


class TrainOut(BaseModel):
    id: int
    train_number: str
    train_name: str
    source_station_code: str
    destination_station_code: str
    departure_time: str
    arrival_time: str
    travel_duration: str
    total_seats: int
    base_fare: float
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TrainSearchResponse(BaseModel):
    train_id: int
    train_number: str
    train_name: str
    source_station_code: str
    destination_station_code: str
    departure_time: str
    arrival_time: str
    travel_duration: str
    journey_date: str
    fare: float
    total_seats: int
    available_seats: int
    availability_status: str  # "AVAILABLE", "FILLING FAST", "SOLD OUT"


# --- Route & Schedule Schemas ---

class RouteStopCreate(BaseModel):
    train_id: int
    station_code: str = Field(min_length=2, max_length=10)
    stop_sequence: int = Field(ge=1)
    arrival_time: Optional[str] = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    departure_time: Optional[str] = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    distance_km: int = Field(default=0, ge=0)

    @field_validator("station_code")
    @classmethod
    def uppercase_station(cls, v: str) -> str:
        return v.strip().upper()


class RouteStopOut(BaseModel):
    id: int
    train_id: int
    station_code: str
    stop_sequence: int
    arrival_time: Optional[str]
    departure_time: Optional[str]
    distance_km: int

    model_config = ConfigDict(from_attributes=True)


class ScheduleCreate(BaseModel):
    train_id: int
    journey_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$", description="Format: YYYY-MM-DD")
    total_seats: int = Field(ge=1)
    available_seats: int = Field(ge=0)
    fare: float = Field(ge=0.0)


class ScheduleOut(BaseModel):
    id: int
    train_id: int
    journey_date: str
    total_seats: int
    available_seats: int
    fare: float
    is_cancelled: bool

    model_config = ConfigDict(from_attributes=True)


# --- Booking Schemas ---

class PassengerInput(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    age: int = Field(ge=1, le=120)
    gender: str = Field(description="'Male', 'Female', or 'Other'")
    berth_preference: Optional[str] = Field(default="None")


class PassengerOut(BaseModel):
    id: int
    name: str
    age: int
    gender: str
    seat_number: str
    berth_preference: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class BookingCreate(BaseModel):
    train_id: int
    journey_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$", description="Format: YYYY-MM-DD")
    passengers: List[PassengerInput] = Field(min_length=1, max_length=6, description="Between 1 and 6 passengers per booking")


class BookingOut(BaseModel):
    id: int
    pnr: str
    user_id: int
    train_id: int
    train_number: str
    train_name: str
    source_station: str
    destination_station: str
    journey_date: str
    total_passengers: int
    total_fare: float
    booking_status: str
    payment_status: str
    created_at: datetime
    cancelled_at: Optional[datetime]
    passengers: List[PassengerOut] = []

    model_config = ConfigDict(from_attributes=True)


class BookingCancelResponse(BaseModel):
    message: str
    pnr: str
    booking_status: str
    seats_released: int
    refund_amount: float
    refund_status: str
