from typing import List, Union, Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.app.models.addon import Addon
from src.app.models.barber import Barber
from src.app.models.barber_schedule import BarberSchedule
from src.app.models.barber_service_link import BarberService
from src.app.models.barber_unavailable_time import BarberUnavailableTime
from src.app.models.service import Service
from src.app.models.user import User
from src.app.schemas.barber import BarberCreate, BarberBase, BarberUpdate, ServiceAssignment
from src.app.schemas.barber_schedule import BarberScheduleCreate, BarberScheduleUpdate, BarberUnavailableTimeCreate, \
    BarberUnavailableTimeUpdate


def create_barber(db: Session, barber: BarberCreate):

    user = db.query(User).filter(User.id == barber.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")


    user.role = "barber"
    new_barber = Barber(**barber.model_dump(exclude="user_id"), user_id=user.id)

    db.add(new_barber)
    db.commit()
    db.refresh(new_barber)
    return new_barber


def get_barbers(db: Session):
    return db.query(Barber).all()


def get_barber(db: Session, barber_id: int):
    return db.query(Barber).filter(Barber.id == barber_id).first()


def update_barber(
        db: Session,
        barber_id: int,
        updated_data: BarberUpdate
):
    barber = get_barber(db, barber_id)
    if barber:
        for key, value in updated_data.model_dump().items():
            setattr(barber, key, value)
        db.commit()
        db.refresh(barber)
    return barber


def delete_barber(db: Session, barber_id: int):
    barber = get_barber(db, barber_id)
    if barber:
        db.delete(barber)
        db.commit()
        return True
    return False


def assign_services_to_barber(
        db: Session,
        barber_id: int,
        assignments: List[ServiceAssignment]
):
    barber = db.query(Barber).filter(Barber.id == barber_id).first()
    if not barber:
        return None

    existing_ids = {service.service_id for service in barber.barber_services}
    print("existing_ids", existing_ids)
    new_assignments = [a for a in assignments if a.service_id not in existing_ids]
    new_ids = [a.service_id for a in new_assignments]
    print("new_ids", new_ids)
    if not new_ids:
        return barber
    print("success")
    new_services = db.query(Service).filter(Service.id.in_(new_ids)).all()
    if len(new_services) != len(new_ids):
        raise HTTPException(status_code=400, detail="Some service IDs were not found")

    # barber.services.extend(new_services)
    for service in new_assignments:
        barber_service = BarberService(
            barber_id=barber.id,
            service_id=service.service_id,
            duration=service.duration
        )
        db.add(barber_service)
    db.commit()
    db.refresh(barber)
    return barber


def assign_addons_to_barber(
        db: Session,
        barber_id: int,
        addon_ids: List[int]
):
    barber = db.query(Barber).filter(Barber.id == barber_id).first()
    if not barber:
        return None

    existing_ids = {addon.id for addon in barber.addons}
    new_ids = set(addon_ids) - existing_ids

    if not new_ids:
        return barber

    new_addons = db.query(Addon).filter(Addon.id.in_(new_ids)).all()

    if len(new_addons) != len(new_ids):
        raise HTTPException(status_code=400, detail="Some addon IDs were not found")

    barber.addons.extend(new_addons)

    db.commit()
    db.refresh(barber)
    return barber


def remove_service_from_barber(
        db: Session, barber_id: int,
        service_id: int
) -> Optional[Barber]:
    barber = db.query(Barber).filter(Barber.id == barber_id).first()
    if not barber:
        return None

    service = next((service for service in barber.barber_services if service.service_id == service_id), None)
    if not service:
        raise HTTPException(status_code=400, detail="Service not assigned to this barber")

    # barber.services.remove(service)
    db.delete(service)
    db.commit()
    db.refresh(barber)
    return barber


def remove_addon_from_barber(
        db: Session,
        barber_id: int,
        addon_id: int
) -> Optional[Barber]:
    barber = db.query(Barber).filter(Barber.id == barber_id).first()
    if not barber:
        return None

    addon = next((addon for addon in barber.addons if addon.id == addon_id), None)
    if not addon:
        raise HTTPException(status_code=400, detail="Addon not assigned to this barber")

    barber.addons.remove(addon)
    db.commit()
    db.refresh(barber)
    return barber


# CRUD for BarberSchedule
def create_barber_schedule(
        db: Session,
        barber_id: int,
        schedule_data: BarberScheduleCreate
) -> BarberSchedule:
    """Creates a new regular schedule entry for a specific barber."""
    db_schedule = BarberSchedule(**schedule_data.model_dump(), barber_id=barber_id)
    db.add(db_schedule)
    db.commit()
    db.refresh(db_schedule)
    return db_schedule


def get_barber_schedules(db: Session, barber_id: int) -> list[BarberSchedule]:
    """Retrieves all regular schedule entries for a specific barber."""
    return db.scalars(
        select(BarberSchedule).where(BarberSchedule.barber_id  == barber_id)
    ).all()


def get_barber_schedule_by_id(db: Session,  schedule_id: int) -> BarberSchedule | None:
    """Retrieves a specific regular schedule entry by its ID."""
    return db.get(BarberSchedule, schedule_id)


def update_barber_schedule(db: Session, schedule_id: int, schedule_data: BarberScheduleUpdate) -> BarberSchedule | None:
    """Updates an existing regular schedule entry."""
    db_schedule = db.get(BarberSchedule, schedule_id)
    if db_schedule:
        for key, value in schedule_data.model_dump(exclude_unset=True).items():
            setattr(db_schedule, key, value)
        db.add(db_schedule)
        db.commit()
        db.refresh(db_schedule)
        return db_schedule


def delete_barber_schedule(db: Session, schedule_id: int) -> bool:
    """Deletes a regular schedule entry."""
    db_schedule = db.get(BarberSchedule, schedule_id)
    if db_schedule:
        db.delete(db_schedule)
        db.commit()
        return True
    return False


# CRUD for BarberUnavailableTime
def create_barber_unavailable_time(db: Session, barber_id: int, unavailable_data: BarberUnavailableTimeCreate) -> BarberUnavailableTime:
    """Creates a new unavailable time entry for a specific barber."""
    db_unavailable_time = BarberUnavailableTime(**unavailable_data.model_dump(), barber_id=barber_id)
    db.add(db_unavailable_time)
    db.commit()
    db.refresh(db_unavailable_time)
    return db_unavailable_time


def get_barber_unavailable_times(db: Session, barber_id: int) -> list[BarberUnavailableTime]:
    """Retrieves all unavailable time entries for a specific barber."""
    return db.scalars(
        select(BarberUnavailableTime).where(BarberUnavailableTime.barber_id == barber_id)
    ).all()


def get_barber_unavailable_time_by_id(db: Session, unavailable_time_id: int) -> BarberUnavailableTime | None:
    """Retrieves a specific unavailable time entry by its ID."""
    return db.get(BarberUnavailableTime, unavailable_time_id)


def update_barber_unavailable_time(
        db: Session,
        unavailable_time_id: int,
        unavailable_data: BarberUnavailableTimeUpdate
) -> BarberUnavailableTime | None:
    """Updates an existing unavailable time entry."""
    db_unavailable_time = db.get(BarberUnavailableTime, unavailable_time_id)
    if db_unavailable_time:
        for key, value in unavailable_data.model_dump(exclude_unset=True).items():
            setattr(db_unavailable_time, key, value)
        db.add(db_unavailable_time)
        db.commit()
        db.refresh(db_unavailable_time)
    return db_unavailable_time


def delete_barber_unavailable_time(
        db: Session,
        unavailable_time_id: int
) -> bool:
    """Deletes an unavailable time entry."""
    db_unavailable_time = db.get(BarberUnavailableTime, unavailable_time_id)
    if db_unavailable_time:
        db.delete(db_unavailable_time)
        db.commit()
        return True
    return False
