from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.app.auth.dependencies import admin_required, get_current_user
from src.app.crud.barber import create_barber_schedule, get_barber_schedules, get_barber_schedule_by_id, \
    update_barber_schedule, delete_barber_schedule, create_barber_unavailable_time, get_barber_unavailable_times, \
    get_barber_unavailable_time_by_id, update_barber_unavailable_time, delete_barber_unavailable_time
from src.app.database import get_db
from src.app.crud import barber as crud
from src.app.models.barber import Barber
from src.app.models.user import User
from src.app.schemas.barber import BarberCreate, BarberRead, BarberBase, AssignServices, BarberUpdate, AssignAddons
from typing import List

from src.app.schemas.barber_schedule import BarberScheduleInDB, BarberScheduleCreate, BarberScheduleUpdate, \
    BarberUnavailableTimeCreate, BarberUnavailableTimeInDB, BarberUnavailableTimeUpdate

router = APIRouter(tags=["Barbers"])


@router.post("/", response_model=BarberRead)
def create_barber(
        barber: BarberCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(admin_required)
):
    return crud.create_barber(db=db, barber=barber)


@router.get("/", response_model=List[BarberRead])
def get_all_barbers(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    return crud.get_barbers(db=db)


@router.put("/{barber_id}", response_model=BarberRead)
def update_barber(
        barber_id: int,
        updated_data: BarberUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(admin_required)
):
    result = crud.update_barber(db=db, barber_id=barber_id, updated_data=updated_data)
    if not result:
        raise HTTPException(status_code=404, detail="Barber not found")
    return result


@router.delete("/{barber_id}", status_code=204)
def delete_barber(
        barber_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(admin_required)
):
    if not crud.delete_barber(db=db, barber_id=barber_id):
        raise HTTPException(status_code=404, detail="Barber not found")


@router.post("/{barber_id}/service", response_model=BarberRead)
def assign_services(
        barber_id: int,
        payload: AssignServices,
        db: Session = Depends(get_db),
        current_user: User = Depends(admin_required)
):
    result = crud.assign_services_to_barber(db, barber_id, payload.service_ids)
    if not result:
        raise HTTPException(status_code=404, detail="Barber not found or invalid service IDs")
    return result


@router.post("/{barber_id}/addon", response_model=BarberRead)
def assign_addons(
        barber_id: int,
        payload: AssignAddons,
        db: Session = Depends(get_db),
        current_user: User = Depends(admin_required)
):
    result = crud.assign_addons_to_barber(db, barber_id, payload.addon_ids)
    if not result:
        raise HTTPException(status_code=404, detail="Barber not found or invalid addon IDs")
    return result


@router.delete("/{barber_id}/service/{service_id}", response_model=BarberRead)
def remove_service(
        barber_id: int,
        service_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(admin_required)
):
    result = crud.remove_service_from_barber(db, barber_id, service_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Invalid service IDs")
    return result


@router.delete("/{barber_id}/addon/{addon_id}", response_model=BarberRead)
def remove_addon(
        barber_id: int,
        addon_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(admin_required)
):
    result = crud.remove_addon_from_barber(db, barber_id, addon_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Invalid addon IDs")
    return result


# Endpoints for Barber Schedules
@router.post("/{barber_id}/schedules/", response_model=BarberScheduleInDB, status_code=status.HTTP_201_CREATED)
def create_schedule_for_barber(
        barber_id: int,
        schedule_data: BarberScheduleCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(admin_required)
):
    """
        Create a new regular working schedule for a specific barber.
        Requires authentication (e.g., admin or the barber themselves).
        """

    barber = db.get(Barber, barber_id)
    if not barber:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Barber not found")

    return create_barber_schedule(db=db, barber_id=barber_id, schedule_data=schedule_data)


@router.get("/{barber_id}/schedules/", response_model=List[BarberScheduleInDB])
def get_schedules_for_barber(
        barber_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Retrieve all regular working schedules for a specific barber.
    """
    barber = db.get(Barber, barber_id)
    if not barber:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Barber not found")

    return get_barber_schedules(db=db, barber_id=barber_id)


@router.get("/schedules/{schedule_id}", response_model=BarberScheduleInDB)
def get_schedule_by_id(
        schedule_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Retrieve a specific regular schedule entry by its ID.
    """
    schedule = get_barber_schedule_by_id(db=db, schedule_id=schedule_id)
    if not schedule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule entry not found")
    return schedule


@router.patch("/schedules/{schedule_id}", response_model=BarberScheduleInDB)
def update_schedule_entry(
        schedule_id: int,
        schedule_data: BarberScheduleUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(admin_required)
):
    """
    Update an existing regular schedule entry.
    """

    updated_schedule = update_barber_schedule(db=db, schedule_id=schedule_id, schedule_data=schedule_data)
    if not updated_schedule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule entry not found")
    return updated_schedule


@router.delete("/schedules/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_schedule_entry(
        schedule_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(admin_required)
):
    """
    Delete a regular schedule entry.
    """
    if not delete_barber_schedule(db=db, schedule_id=schedule_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule entry not found")
    return {"message": "Schedule entry deleted successfully"}


# Endpoints for Barber Unavailable Times
@router.post("/{barber_id}/unavailable-times/", response_model=BarberUnavailableTimeInDB, status_code=status.HTTP_201_CREATED)
def create_unavailable_time_for_barber(
        barber_id: int,
        unavailable_data: BarberUnavailableTimeCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(admin_required)
):
    """
    Create a new unavailable time entry for a specific barber.
    """
    barber = db.get(Barber, barber_id)
    if not barber:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Barber not found")

    return create_barber_unavailable_time(db=db, barber_id=barber_id, unavailable_data=unavailable_data)


@router.get("/{barber_id}/unavailable-times/", response_model=List[BarberUnavailableTimeInDB])
def get_unavailable_times_for_barber(
    barber_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve all unavailable time entries for a specific barber.
    """
    barber = db.get(Barber, barber_id)
    if not barber:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Barber not found")

    return get_barber_unavailable_times(db=db, barber_id=barber_id)


@router.get("/unavailable-times/{unavailable_time_id}", response_model=BarberUnavailableTimeInDB)
def get_unavailable_time_by_id(
        unavailable_time_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(admin_required)
):
    """
    Retrieve a specific unavailable time entry by its ID.
    """
    unavailable_time = get_barber_unavailable_time_by_id(db=db, unavailable_time_id=unavailable_time_id)
    if not unavailable_time:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unavailable time entry not found")
    return unavailable_time


@router.patch("/unavailable-times/{unavailable_time_id}", response_model=BarberUnavailableTimeInDB)
def update_unavailable_time_entry( # Changed to 'def'
    unavailable_time_id: int,
    unavailable_data: BarberUnavailableTimeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_required)
):
    """
    Update an existing unavailable time entry.
    """
    updated_unavailable_time = update_barber_unavailable_time(
        db=db,
        unavailable_time_id=unavailable_time_id,
        unavailable_data=unavailable_data
    )
    if not updated_unavailable_time:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unavailable time entry not found")
    return updated_unavailable_time


@router.delete("/unavailable-times/{unavailable_time_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_unavailable_time_entry(
    unavailable_time_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_required)
):
    """
    Delete an unavailable time entry.
    """
    if not delete_barber_unavailable_time(
            db=db,
            unavailable_time_id=unavailable_time_id
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unavailable time entry not found")
    return {"message": "Unavailable time entry deleted successfully"}
