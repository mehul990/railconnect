from sqlmodel import Session, select
from datetime import datetime, timedelta, timezone
from app.database import engine, init_db
from app.models import User, Station, Train, TrainRouteStop, TrainSchedule
from app.security import hash_password
from app.config import settings
import logging

logger = logging.getLogger("railconnect.seed")


def seed_database():
    """Populate database with initial admin, passenger, stations, trains, and schedules."""
    init_db()
    with Session(engine) as session:
        # 1. Seed Admin
        admin = session.exec(select(User).where(User.email == settings.INITIAL_ADMIN_EMAIL)).first()
        if not admin:
            admin = User(
                email=settings.INITIAL_ADMIN_EMAIL,
                full_name=settings.INITIAL_ADMIN_NAME,
                hashed_password=hash_password(settings.INITIAL_ADMIN_PASSWORD),
                role="admin",
                is_active=True
            )
            session.add(admin)

        # 2. Seed Default Passenger
        passenger = session.exec(select(User).where(User.email == "passenger@railconnect.com")).first()
        if not passenger:
            passenger = User(
                email="passenger@railconnect.com",
                full_name="Aarav Sharma",
                hashed_password=hash_password("Passenger@123"),
                role="passenger",
                is_active=True
            )
            session.add(passenger)
        
        session.commit()

        # 3. Seed Stations
        stations_data = [
            {"code": "NDLS", "name": "New Delhi Railway Station", "city": "New Delhi", "state": "Delhi"},
            {"code": "CNB", "name": "Kanpur Central Railway Station", "city": "Kanpur", "state": "Uttar Pradesh"},
            {"code": "LKO", "name": "Lucknow Charbagh Railway Station", "city": "Lucknow", "state": "Uttar Pradesh"},
            {"code": "PRYJ", "name": "Prayagraj Junction", "city": "Prayagraj", "state": "Uttar Pradesh"},
            {"code": "BSB", "name": "Varanasi Junction", "city": "Varanasi", "state": "Uttar Pradesh"},
            {"code": "MMCT", "name": "Mumbai Central", "city": "Mumbai", "state": "Maharashtra"}
        ]

        for s_data in stations_data:
            existing = session.exec(select(Station).where(Station.code == s_data["code"])).first()
            if not existing:
                session.add(Station(**s_data))
        
        session.commit()

        # 4. Seed Trains
        trains_data = [
            {
                "train_number": "12004",
                "train_name": "New Delhi - Kanpur Shatabdi Express",
                "source_station_code": "NDLS",
                "destination_station_code": "CNB",
                "departure_time": "06:10",
                "arrival_time": "11:20",
                "travel_duration": "5h 10m",
                "total_seats": 120,
                "base_fare": 750.0,
                "is_active": True
            },
            {
                "train_number": "12452",
                "train_name": "Shram Shakti Express",
                "source_station_code": "NDLS",
                "destination_station_code": "CNB",
                "departure_time": "23:55",
                "arrival_time": "06:00",
                "travel_duration": "6h 05m",
                "total_seats": 150,
                "base_fare": 480.0,
                "is_active": True
            },
            {
                "train_number": "22436",
                "train_name": "Vande Bharat Express",
                "source_station_code": "NDLS",
                "destination_station_code": "BSB",
                "departure_time": "06:00",
                "arrival_time": "14:00",
                "travel_duration": "8h 00m",
                "total_seats": 100,
                "base_fare": 1750.0,
                "is_active": True
            },
            {
                "train_number": "12952",
                "train_name": "Mumbai Tejas Rajdhani Express",
                "source_station_code": "MMCT",
                "destination_station_code": "NDLS",
                "departure_time": "17:00",
                "arrival_time": "08:30",
                "travel_duration": "15h 30m",
                "total_seats": 200,
                "base_fare": 2400.0,
                "is_active": True
            }
        ]

        saved_trains = {}
        for t_data in trains_data:
            existing = session.exec(select(Train).where(Train.train_number == t_data["train_number"])).first()
            if not existing:
                t = Train(**t_data)
                session.add(t)
                session.commit()
                session.refresh(t)
                saved_trains[t.train_number] = t
            else:
                saved_trains[existing.train_number] = existing

        # 5. Seed Route Stop for Vande Bharat (NDLS -> CNB -> BSB)
        vande_bharat = saved_trains.get("22436")
        if vande_bharat:
            existing_stop = session.exec(
                select(TrainRouteStop)
                .where(TrainRouteStop.train_id == vande_bharat.id)
                .where(TrainRouteStop.station_code == "CNB")
            ).first()
            if not existing_stop:
                stop = TrainRouteStop(
                    train_id=vande_bharat.id,
                    station_code="CNB",
                    stop_sequence=1,
                    arrival_time="10:08",
                    departure_time="10:10",
                    distance_km=440
                )
                session.add(stop)
                session.commit()

        # 6. Seed Schedules for upcoming 14 days
        today = datetime.now(timezone.utc).date()
        for train in saved_trains.values():
            for day_offset in range(14):
                journey_date_str = (today + timedelta(days=day_offset)).strftime("%Y-%m-%d")
                sched = session.exec(
                    select(TrainSchedule)
                    .where(TrainSchedule.train_id == train.id)
                    .where(TrainSchedule.journey_date == journey_date_str)
                ).first()
                if not sched:
                    session.add(
                        TrainSchedule(
                            train_id=train.id,
                            journey_date=journey_date_str,
                            total_seats=train.total_seats,
                            available_seats=train.total_seats,
                            fare=train.base_fare,
                            is_cancelled=False
                        )
                    )
        session.commit()
        print("Database initialized and sample railway data seeded successfully.")


if __name__ == "__main__":
    seed_database()
