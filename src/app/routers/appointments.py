from datetime import datetime, timedelta, UTC, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from src.app import crud
from src.app.auth.dependencies import get_current_user, admin_required, barber_required
from src.app.database import get_db
from src.app.crud.appointment import create_appointment as create_appointment_crud, get_appointment_by_barber

from typing import List

from src.app.models.appointment import Appointment
from src.app.models.barber import Barber
from src.app.models.service import Service
from src.app.models.user import User
from src.app.schemas.appointment import AppointmentCreate, AppointmentReadDetailed, AppointmentResponse, \
    AppointmentGroupedUserView, AppointmentShortUserView, AddonsOut, AppointmentUpdate
from src.app.services.timeslot_generator import check_availability_on_create, check_availability_on_edit

router = APIRouter()


@router.post("/", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
def create_appointment(
        appointment: AppointmentCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    check_availability_on_create(
        db=db,
        barber_id=appointment.barber_id,
        scheduled_time=appointment.scheduled_time,
        service_id=appointment.service_id,
        addon_ids=appointment.addon_ids)  # check_availability
    created_appointment = create_appointment_crud(db=db, data=appointment, user_id=current_user.id)

    return created_appointment

@router.patch("/{appointment_id}", response_model=AppointmentReadDetailed)
def update_appointment(
        appointment: AppointmentUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    check_availability_on_edit(
        db=db,
        appointment_id=appointment.appointment_id,
        scheduled_time=appointment.scheduled_time,
    )
    updated_appointment = crud.appointment.update_appointment(db=db, new_appointment=appointment)

    return updated_appointment

@router.get("/barber/{barber_id}", response_model=List[AppointmentResponse])
def get_appointments_by_barber(
        barber_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(admin_required)
):
    try:
        appointments_from_db = get_appointment_by_barber(db, barber_id)
        return appointments_from_db
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_appointment(
        appointment_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    if appointment.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="You can't delete this appointment")

    db.delete(appointment)
    db.commit()


@router.get("/me", response_model=AppointmentGroupedUserView)
def get_user_appointments(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    now = datetime.now(timezone.utc)

    appointments = (
        db.query(Appointment)
        .filter(Appointment.user_id == current_user.id)
        .options(
            joinedload(Appointment.service),
            joinedload(Appointment.addons),
            joinedload(Appointment.barber)
        )
        .all()
    )

    def to_short_view(a: Appointment) -> AppointmentShortUserView:
        start = a.scheduled_time or datetime.now(UTC)
        
        # Ensure start is timezone-aware
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)

        end = start + timedelta(minutes=a.total_duration)

        full_service_title = " + ".join([a.service.name] + [addon.name for addon in a.addons])

        return AppointmentShortUserView(
            id=a.id,
            barber_name=a.barber.name,
            full_service_title=full_service_title,
            scheduled_day=start.strftime("%A"),
            scheduled_date=start.strftime("%d.%m.%Y"),
            scheduled_time=f"{start.strftime('%H:%M')} - {end.strftime('%H:%M')}",
            total_price=a.total_price
        )

    # Ensure all scheduled times are timezone-aware for comparison
    upcoming = []
    completed = []
    
    for a in appointments:
        scheduled_time = a.scheduled_time
        if scheduled_time.tzinfo is None:
            scheduled_time = scheduled_time.replace(tzinfo=timezone.utc)
        
        if scheduled_time > now:
            upcoming.append(to_short_view(a))
        else:
            completed.append(to_short_view(a))

    return {
        "upcoming": upcoming,
        "completed": completed
    }


@router.get("/me/barber", response_model=List[AppointmentResponse])
def get_appointments_by_barber(
        db: Session = Depends(get_db),
        current_user: User = Depends(barber_required)
):
    try:
        appointments_from_db = get_appointment_by_barber(db, current_user.id)
        return appointments_from_db
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))