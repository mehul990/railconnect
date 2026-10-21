from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select
from typing import List, Optional
from datetime import datetime, date, timezone

from app.database import get_session
from app.models import Train, Station, TrainSchedule, TrainRouteStop
from app.schemas import TrainSearchResponse, StationOut, TrainOut

router = APIRouter(prefix="/trains", tags=["Find a Train"])


@router.get("/stations", response_model=List[StationOut])
def get_stations(session: Session = Depends(get_session)):
    """List all available stations for passenger route selection."""
    stations = session.exec(select(Station)).all()
    return stations


@router.get("/search", response_model=List[TrainSearchResponse])
def search_trains(
    source: str = Query(..., description="Starting station code (e.g. NDLS)", min_length=2, max_length=10),
    destination: str = Query(..., description="Destination station code (e.g. CNB)", min_length=2, max_length=10),
    journey_date: str = Query(..., description="Journey date in YYYY-MM-DD format", pattern=r"^\d{4}-\d{2}-\d{2}$"),
    session: Session = Depends(get_session)
):
    """
    Search available trains between two stations for a given date.
    Displays departure, arrival, duration, fare, available seats, and availability status.
    Handles invalid routes and past dates with informative error messages.
    """
    src_code = source.strip().upper()
    dst_code = destination.strip().upper()

    if src_code == dst_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source and destination stations cannot be the same"
        )
    
    # Validate date
    try:
        parsed_date = datetime.strptime(journey_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid journey date format. Please use YYYY-MM-DD."
        )
    
    today = datetime.now(timezone.utc).date()
    if parsed_date < today:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Journey date cannot be in the past"
        )
    
    # Validate stations exist
    src_station = session.exec(select(Station).where(Station.code == src_code)).first()
    dst_station = session.exec(select(Station).where(Station.code == dst_code)).first()
    
    if not src_station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Origin station code '{src_code}' was not found in railway directory"
        )
    if not dst_station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Destination station code '{dst_code}' was not found in railway directory"
        )
    
    # Search active trains matching source and destination
    # Check 1: Direct trains
    active_trains = session.exec(
        select(Train)
        .where(Train.is_active == True)
    ).all()

    matching_trains = []

    for train in active_trains:
        # Check direct origin -> destination
        if train.source_station_code == src_code and train.destination_station_code == dst_code:
            matching_trains.append((train, train.departure_time, train.arrival_time, train.travel_duration, train.base_fare))
            continue
        
        # Check intermediate stops
        stops = session.exec(
            select(TrainRouteStop)
            .where(TrainRouteStop.train_id == train.id)
            .order_by(TrainRouteStop.stop_sequence)
        ).all()

        if stops:
            # Build full ordered station sequence: source, stops, destination
            all_stops = [(train.source_station_code, 0, train.departure_time, train.departure_time)]
            for s in stops:
                all_stops.append((s.station_code, s.stop_sequence, s.arrival_time or "", s.departure_time or ""))
            all_stops.append((train.destination_station_code, 9999, train.arrival_time, train.arrival_time))

            src_idx = -1
            dst_idx = -1
            src_dep = ""
            dst_arr = ""

            for idx, (st_code, seq, arr, dep) in enumerate(all_stops):
                if st_code == src_code and src_idx == -1:
                    src_idx = idx
                    src_dep = dep
                if st_code == dst_code and src_idx != -1:
                    dst_idx = idx
                    dst_arr = arr
                    break

            if src_idx != -1 and dst_idx != -1 and src_idx < dst_idx:
                matching_trains.append((train, src_dep or train.departure_time, dst_arr or train.arrival_time, train.travel_duration, train.base_fare))

    response_items: List[TrainSearchResponse] = []

    for train, dep_time, arr_time, duration, fare in matching_trains:
        # Check or initialize seat inventory for this journey date
        schedule = session.exec(
            select(TrainSchedule)
            .where(TrainSchedule.train_id == train.id)
            .where(TrainSchedule.journey_date == journey_date)
        ).first()

        if not schedule:
            schedule = TrainSchedule(
                train_id=train.id,
                journey_date=journey_date,
                total_seats=train.total_seats,
                available_seats=train.total_seats,
                fare=fare,
                is_cancelled=False
            )
            session.add(schedule)
            session.commit()
            session.refresh(schedule)

        if schedule.is_cancelled:
            continue

        available = schedule.available_seats
        if available == 0:
            status_text = "SOLD OUT"
        elif available <= 10:
            status_text = "FILLING FAST"
        else:
            status_text = "AVAILABLE"

        response_items.append(
            TrainSearchResponse(
                train_id=train.id,
                train_number=train.train_number,
                train_name=train.train_name,
                source_station_code=src_code,
                destination_station_code=dst_code,
                departure_time=dep_time,
                arrival_time=arr_time,
                travel_duration=duration,
                journey_date=journey_date,
                fare=schedule.fare,
                total_seats=schedule.total_seats,
                available_seats=available,
                availability_status=status_text
            )
        )

    return response_items
