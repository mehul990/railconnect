from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List
from datetime import datetime, timezone, date

from app.database import get_session, booking_lock
from app.models import User, Train, TrainSchedule, Booking, Passenger
from app.schemas import (
    BookingCreate, BookingOut, PassengerOut,
    BookingCancelResponse, MessageResponse
)
from app.security import generate_pnr
from app.dependencies import get_current_user

router = APIRouter(prefix="/bookings", tags=["Book a Ticket"])


@router.post("", response_model=BookingOut, status_code=status.HTTP_201_CREATED)
def book_ticket(
    booking_in: BookingCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Book train tickets for one or more passengers with atomic seat deduction and PNR generation.
    Protected against race conditions and overbooking using atomic transactions and concurrency locks.
    """
    train = session.get(Train, booking_in.train_id)
    if not train or not train.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The requested train is not available or has been deactivated"
        )
    
    # Validate date
    try:
        journey_d = datetime.strptime(booking_in.journey_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid journey date format. Please use YYYY-MM-DD."
        )
    
    if journey_d < datetime.now(timezone.utc).date():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot book tickets for past dates"
        )
    
    num_passengers = len(booking_in.passengers)
    if num_passengers < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one passenger is required for booking"
        )
    
    # Concurrency safe block
    with booking_lock:
        # Retrieve or initialize schedule for this train and journey date
        schedule = session.exec(
            select(TrainSchedule)
            .where(TrainSchedule.train_id == train.id)
            .where(TrainSchedule.journey_date == booking_in.journey_date)
        ).first()

        if not schedule:
            schedule = TrainSchedule(
                train_id=train.id,
                journey_date=booking_in.journey_date,
                total_seats=train.total_seats,
                available_seats=train.total_seats,
                fare=train.base_fare,
                is_cancelled=False
            )
            session.add(schedule)
            session.commit()
            session.refresh(schedule)

        if schedule.is_cancelled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This train journey has been cancelled for the selected date"
            )

        if schedule.available_seats < num_passengers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient seats available. Requested: {num_passengers}, Available: {schedule.available_seats}"
            )

        # Allocate seat numbers
        starting_seat = schedule.total_seats - schedule.available_seats + 1
        allocated_passengers = []
        for idx, p_input in enumerate(booking_in.passengers):
            seat_num = f"B1-{starting_seat + idx}"
            allocated_passengers.append((p_input, seat_num))

        # Deduct seats atomically
        schedule.available_seats -= num_passengers
        session.add(schedule)

        # Generate unique PNR
        pnr = generate_pnr()
        while session.exec(select(Booking).where(Booking.pnr == pnr)).first():
            pnr = generate_pnr()

        total_fare = round(schedule.fare * num_passengers, 2)

        booking = Booking(
            pnr=pnr,
            user_id=current_user.id,
            train_id=train.id,
            train_number=train.train_number,
            train_name=train.train_name,
            source_station=train.source_station_code,
            destination_station=train.destination_station_code,
            journey_date=booking_in.journey_date,
            total_passengers=num_passengers,
            total_fare=total_fare,
            booking_status="CONFIRMED",
            payment_status="COMPLETED"
        )
        session.add(booking)
        session.commit()
        session.refresh(booking)

        # Save passenger records
        saved_passengers = []
        for p_input, seat_num in allocated_passengers:
            passenger = Passenger(
                booking_id=booking.id,
                name=p_input.name,
                age=p_input.age,
                gender=p_input.gender,
                seat_number=seat_num,
                berth_preference=p_input.berth_preference or "None"
            )
            session.add(passenger)
            saved_passengers.append(passenger)
        
        session.commit()

        # Build response
        p_outs = [
            PassengerOut(
                id=p.id,
                name=p.name,
                age=p.age,
                gender=p.gender,
                seat_number=p.seat_number,
                berth_preference=p.berth_preference
            )
            for p in saved_passengers
        ]

        return BookingOut(
            id=booking.id,
            pnr=booking.pnr,
            user_id=booking.user_id,
            train_id=booking.train_id,
            train_number=booking.train_number,
            train_name=booking.train_name,
            source_station=booking.source_station,
            destination_station=booking.destination_station,
            journey_date=booking.journey_date,
            total_passengers=booking.total_passengers,
            total_fare=booking.total_fare,
            booking_status=booking.booking_status,
            payment_status=booking.payment_status,
            created_at=booking.created_at,
            cancelled_at=booking.cancelled_at,
            passengers=p_outs
        )


@router.get("/my-bookings", response_model=List[BookingOut])
def get_my_bookings(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Retrieve booking history for the authenticated user only."""
    bookings = session.exec(
        select(Booking)
        .where(Booking.user_id == current_user.id)
        .order_by(Booking.created_at.desc())
    ).all()

    result = []
    for b in bookings:
        passengers = session.exec(select(Passenger).where(Passenger.booking_id == b.id)).all()
        p_outs = [
            PassengerOut(
                id=p.id,
                name=p.name,
                age=p.age,
                gender=p.gender,
                seat_number=p.seat_number,
                berth_preference=p.berth_preference
            )
            for p in passengers
        ]
        result.append(
            BookingOut(
                id=b.id,
                pnr=b.pnr,
                user_id=b.user_id,
                train_id=b.train_id,
                train_number=b.train_number,
                train_name=b.train_name,
                source_station=b.source_station,
                destination_station=b.destination_station,
                journey_date=b.journey_date,
                total_passengers=b.total_passengers,
                total_fare=b.total_fare,
                booking_status=b.booking_status,
                payment_status=b.payment_status,
                created_at=b.created_at,
                cancelled_at=b.cancelled_at,
                passengers=p_outs
            )
        )
    return result


@router.get("/{pnr}", response_model=BookingOut)
def get_booking_by_pnr(
    pnr: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Look up a specific booking by PNR. Passengers may view only their own bookings; Admins may view any."""
    clean_pnr = pnr.strip().upper()
    booking = session.exec(select(Booking).where(Booking.pnr == clean_pnr)).first()
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No booking found for PNR '{clean_pnr}'"
        )
    
    # Ownership isolation check
    if current_user.role != "admin" and booking.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You are not authorized to view another passenger's booking"
        )
    
    passengers = session.exec(select(Passenger).where(Passenger.booking_id == booking.id)).all()
    p_outs = [
        PassengerOut(
            id=p.id,
            name=p.name,
            age=p.age,
            gender=p.gender,
            seat_number=p.seat_number,
            berth_preference=p.berth_preference
        )
        for p in passengers
    ]

    return BookingOut(
        id=booking.id,
        pnr=booking.pnr,
        user_id=booking.user_id,
        train_id=booking.train_id,
        train_number=booking.train_number,
        train_name=booking.train_name,
        source_station=booking.source_station,
        destination_station=booking.destination_station,
        journey_date=booking.journey_date,
        total_passengers=booking.total_passengers,
        total_fare=booking.total_fare,
        booking_status=booking.booking_status,
        payment_status=booking.payment_status,
        created_at=booking.created_at,
        cancelled_at=booking.cancelled_at,
        passengers=p_outs
    )


@router.post("/{pnr}/cancel", response_model=BookingCancelResponse)
def cancel_booking(
    pnr: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Cancel an eligible booking and release seats back to the inventory atomically.
    Prevents repeated cancellation and double seat release.
    """
    clean_pnr = pnr.strip().upper()

    with booking_lock:
        booking = session.exec(select(Booking).where(Booking.pnr == clean_pnr)).first()
        if not booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No booking found for PNR '{clean_pnr}'"
            )
        
        # User authorization
        if current_user.role != "admin" and booking.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: You cannot cancel a booking that does not belong to you"
            )
        
        # Prevent repeated seat release
        if booking.booking_status == "CANCELLED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This booking has already been cancelled. Repeated cancellation is prohibited."
            )
        
        # Check if journey date is past
        try:
            journey_d = datetime.strptime(booking.journey_date, "%Y-%m-%d").date()
            if journey_d < datetime.now(timezone.utc).date():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot cancel tickets for a journey that has already commenced or concluded"
                )
        except ValueError:
            pass

        # Update seat availability
        schedule = session.exec(
            select(TrainSchedule)
            .where(TrainSchedule.train_id == booking.train_id)
            .where(TrainSchedule.journey_date == booking.journey_date)
        ).first()

        if schedule:
            schedule.available_seats = min(schedule.total_seats, schedule.available_seats + booking.total_passengers)
            session.add(schedule)

        # Update booking status
        booking.booking_status = "CANCELLED"
        booking.cancelled_at = datetime.now(timezone.utc)
        session.add(booking)
        session.commit()

        return BookingCancelResponse(
            message=f"Booking {booking.pnr} has been successfully cancelled.",
            pnr=booking.pnr,
            booking_status="CANCELLED",
            seats_released=booking.total_passengers,
            refund_amount=booking.total_fare,
            refund_status="PROCESSED_SIMULATED"
        )
