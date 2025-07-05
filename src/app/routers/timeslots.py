from datetime import datetime, date
from typing import List

from fastapi import APIRouter, Query, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.app.auth.dependencies import get_current_user
from src.app.database import get_db
from src.app.models.barber import Barber
from src.app.models.service import Service
from src.app.models.user import User
from src.app.services.timeslot_generator import get_available_timeslots, check_availability

router = APIRouter()


@router.get("/available", response_model=List[datetime])
def get_barber_available_timeslots(
        barber_id: int,
        target_date: date = Query(..., description="Date for which to get available timeslots (YYYY-MM-DD)."),
        service_id: int = Query(..., description="ID of the service to book (determines duration)."),
        addons: List[int] = Query([], description="IDs of addons to include in the booking."),
        slot_interval_minutes: int = Query(
            50, ge=1, description="Granularity of slots in minutes (e.g., 15, 30)."),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Get available timeslots for a specific barber on a given date for a particular service.
    This endpoint allows clients to query for free slots before making a booking.
    """
    barber = db.get(Barber, barber_id)
    if not barber:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Barber not found.")

    service = db.get(Service, service_id)
    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found.")

    try:
        # check_availability(db=db, barber_id=barber_id, scheduled_time=datetime.combine(target_date, datetime.min.time()), service_id=service_id)
        available_slots = get_available_timeslots(
            db=db,
            barber_id=barber_id,
            target_date=target_date,
            service_id=service_id,
            slot_interval_minutes=slot_interval_minutes,
            addon_ids=addons

        )
        return available_slots
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"An unexpected error occurred: {e}")
