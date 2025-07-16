from typing import List

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from src.app.models.addon import Addon
from src.app.models.appointment import Appointment
from src.app.models.barber import Barber
from src.app.models.service import Service
from src.app.schemas.appointment import AppointmentCreate


def create_appointment(db: Session, data: AppointmentCreate, user_id: int) -> Appointment:
    service = db.query(Service).filter(Service.id == data.service_id).first()
    if not service:
        raise HTTPException(status_code=400, detail="Service not found")

    barber = db.query(Barber).filter(Barber.id == data.barber_id).first()
    if not barber:
        raise HTTPException(status_code=400, detail="Barber not found")

    barber_service = next(
        (bs for bs in barber.barber_services if bs.service_id == service.id),
        None
    )
    if not barber_service:
        raise HTTPException(status_code=400, detail="This barber does not provide the selected service")

    addons = []
    if data.addon_ids:
        addons = db.query(Addon).filter(Addon.id.in_(data.addon_ids)).all()
        if len(addons) != len(data.addon_ids):
            raise HTTPException(status_code=400, detail="Some addon IDs not found")

    total_price = service.price + sum(addon.price for addon in addons)
    total_duration = barber_service.duration + sum(addon.duration for addon in addons)
    appointment_model = Appointment(
        name=data.name,
        phone_number=data.phone_number,
        barber_id=data.barber_id,
        service_id=data.service_id,
        total_duration=total_duration,
        total_price=total_price,
        scheduled_time=data.scheduled_time,
        user_id=user_id,
        addons=addons
    )
    db.add(appointment_model)
    db.commit()
    db.refresh(appointment_model)

    return db.query(Appointment).options(
        joinedload(Appointment.barber),
        joinedload(Appointment.service),
        joinedload(Appointment.addons),
    ).filter(Appointment.id == appointment_model.id).first()


def get_appointment_by_barber(db: Session, barber_id: int) -> List[Appointment]:
    appointments = db.query(Appointment).filter(Appointment.barber_id == barber_id).options(
        joinedload(Appointment.barber),
        joinedload(Appointment.service),
        joinedload(Appointment.addons)
    ).all()

    for appt in appointments:
        print(f"DEBUG (GET_BY_BARBER): Appointment ID: {appt.id}")
        print(f"DEBUG (GET_BY_BARBER): Has barber attribute? {hasattr(appt, 'barber')}")
        if hasattr(appt, 'barber') and appt.barber:
            print(f"DEBUG (GET_BY_BARBER): Barber object: {appt.barber.name}")
        else:
            print(f"DEBUG (GET_BY_BARBER): Barber object is None or not loaded. (ID: {appt.barber_id})")

        print(f"DEBUG (GET_BY_BARBER): Has service attribute? {hasattr(appt, 'service')}")
        if hasattr(appt, 'service') and appt.service:
            print(f"DEBUG (GET_BY_BARBER): Service object: {appt.service.name}")
        else:
            print(f"DEBUG (GET_BY_BARBER): Service object is None or not loaded. (ID: {appt.service_id})")
        print("-" * 30)

    return appointments


def delete_appointment(db: Session, appointment_id: int) -> bool:
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        return False

    db.delete(appointment)
    db.commit()
    return True
