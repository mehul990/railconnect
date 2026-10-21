from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List, Optional

from app.database import get_session
from app.models import User, Train, Station, TrainRouteStop, TrainSchedule
from app.schemas import (
    StationCreate, StationOut,
    TrainCreate, TrainUpdate, TrainOut,
    RouteStopCreate, RouteStopOut,
    ScheduleCreate, ScheduleOut,
    MessageResponse
)
from app.dependencies import get_current_admin

router = APIRouter(prefix="/admin", tags=["Admin Control"])


# --- Stations ---

@router.post("/stations", response_model=StationOut, status_code=status.HTTP_201_CREATED)
def create_station(
    station_in: StationCreate,
    admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session)
):
    """Add a new railway station (Admin only)."""
    existing = session.exec(select(Station).where(Station.code == station_in.code)).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Station with code '{station_in.code}' already exists"
        )
    
    station = Station.model_validate(station_in)
    session.add(station)
    session.commit()
    session.refresh(station)
    return station


@router.get("/stations", response_model=List[StationOut])
def list_stations(
    admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session)
):
    """List all registered railway stations (Admin only)."""
    stations = session.exec(select(Station)).all()
    return stations


# --- Trains ---

@router.post("/trains", response_model=TrainOut, status_code=status.HTTP_201_CREATED)
def create_train(
    train_in: TrainCreate,
    admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session)
):
    """Add a new train with timings, fare, and seat capacity (Admin only)."""
    existing = session.exec(select(Train).where(Train.train_number == train_in.train_number)).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Train with number '{train_in.train_number}' already exists"
        )
    
    # Verify stations exist
    src = session.exec(select(Station).where(Station.code == train_in.source_station_code)).first()
    dst = session.exec(select(Station).where(Station.code == train_in.destination_station_code)).first()
    if not src or not dst:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Source ({train_in.source_station_code}) or Destination ({train_in.destination_station_code}) station does not exist. Please register the stations first."
        )
    
    train = Train.model_validate(train_in)
    session.add(train)
    session.commit()
    session.refresh(train)
    return train


@router.get("/trains", response_model=List[TrainOut])
def list_all_trains(
    admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session)
):
    """List all trains including active and deactivated (Admin only)."""
    trains = session.exec(select(Train)).all()
    return trains


@router.get("/trains/{train_id}", response_model=TrainOut)
def get_train_details(
    train_id: int,
    admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session)
):
    """Get train details by ID (Admin only)."""
    train = session.get(Train, train_id)
    if not train:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Train not found")
    return train


@router.put("/trains/{train_id}", response_model=TrainOut)
def update_train(
    train_id: int,
    train_in: TrainUpdate,
    admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session)
):
    """Update train metadata, timings, fare, or seat capacity (Admin only)."""
    train = session.get(Train, train_id)
    if not train:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Train not found")
    
    update_data = train_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(train, field, value)
    
    session.add(train)
    session.commit()
    session.refresh(train)
    return train


@router.patch("/trains/{train_id}/deactivate", response_model=TrainOut)
def deactivate_train(
    train_id: int,
    admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session)
):
    """Deactivate a train (Admin only)."""
    train = session.get(Train, train_id)
    if not train:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Train not found")
    
    train.is_active = False
    session.add(train)
    session.commit()
    session.refresh(train)
    return train


@router.patch("/trains/{train_id}/activate", response_model=TrainOut)
def activate_train(
    train_id: int,
    admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session)
):
    """Reactivate a previously deactivated train (Admin only)."""
    train = session.get(Train, train_id)
    if not train:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Train not found")
    
    train.is_active = True
    session.add(train)
    session.commit()
    session.refresh(train)
    return train


@router.delete("/trains/{train_id}", response_model=MessageResponse)
def delete_train(
    train_id: int,
    admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session)
):
    """Soft delete/deactivate train (Admin only)."""
    train = session.get(Train, train_id)
    if not train:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Train not found")
    
    train.is_active = False
    session.add(train)
    session.commit()
    return MessageResponse(message=f"Train {train.train_number} ({train.train_name}) has been deactivated.")


# --- Routes & Stops ---

@router.post("/routes", response_model=RouteStopOut, status_code=status.HTTP_201_CREATED)
def add_route_stop(
    stop_in: RouteStopCreate,
    admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session)
):
    """Add an intermediate route stop to a train (Admin only)."""
    train = session.get(Train, stop_in.train_id)
    if not train:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Train not found")
    
    station = session.exec(select(Station).where(Station.code == stop_in.station_code)).first()
    if not station:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Station '{stop_in.station_code}' not found")
    
    stop = TrainRouteStop.model_validate(stop_in)
    session.add(stop)
    session.commit()
    session.refresh(stop)
    return stop


@router.get("/trains/{train_id}/routes", response_model=List[RouteStopOut])
def get_train_routes(
    train_id: int,
    admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session)
):
    """List all intermediate route stops for a train ordered by sequence (Admin only)."""
    stops = session.exec(
        select(TrainRouteStop)
        .where(TrainRouteStop.train_id == train_id)
        .order_by(TrainRouteStop.stop_sequence)
    ).all()
    return stops


# --- Schedules & Inventory Management ---

@router.post("/schedules", response_model=ScheduleOut, status_code=status.HTTP_201_CREATED)
def set_schedule_inventory(
    sched_in: ScheduleCreate,
    admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session)
):
    """Set or update train seat availability and fare for a specific journey date (Admin only)."""
    train = session.get(Train, sched_in.train_id)
    if not train:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Train not found")
    
    existing = session.exec(
        select(TrainSchedule)
        .where(TrainSchedule.train_id == sched_in.train_id)
        .where(TrainSchedule.journey_date == sched_in.journey_date)
    ).first()
    
    if existing:
        existing.total_seats = sched_in.total_seats
        existing.available_seats = sched_in.available_seats
        existing.fare = sched_in.fare
        session.add(existing)
        session.commit()
        session.refresh(existing)
        return existing
    
    schedule = TrainSchedule.model_validate(sched_in)
    session.add(schedule)
    session.commit()
    session.refresh(schedule)
    return schedule


@router.get("/trains/{train_id}/schedules", response_model=List[ScheduleOut])
def list_train_schedules(
    train_id: int,
    admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session)
):
    """View schedule and seat inventory for a train across dates (Admin only)."""
    schedules = session.exec(
        select(TrainSchedule).where(TrainSchedule.train_id == train_id)
    ).all()
    return schedules
