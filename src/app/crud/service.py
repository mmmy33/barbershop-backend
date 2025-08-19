from typing import List

from sqlalchemy.orm import Session, joinedload

from src.app.models.service import Service
from src.app.models.barber_service_link import BarberService
from src.app.schemas.service import ServiceCreate, ServiceBase, ServiceUpdate, BarberDurationInfo


def create_service(db: Session, service: ServiceCreate):
    new_service = Service(**service.model_dump())
    db.add(new_service)
    db.commit()
    db.refresh(new_service)
    return new_service

def get_services_by_barber(db: Session, barber_id: int):
    barber_services = db.query(BarberService).filter(BarberService.barber_id == barber_id).all()
    return barber_services

def get_services(db: Session):
    return db.query(Service).options(
            joinedload(Service.barber_services).joinedload(BarberService.barber)
        ).all()



def get_service(db: Session, service_id: int):
    return db.query(Service).filter(Service.id == service_id).first()


def update_service(db: Session, service_id: int, updated_data: ServiceUpdate):
    service = get_service(db, service_id)
    if service:
        for key, value in updated_data.model_dump(exclude_unset=True).items():
            if value is not None:  # Only update if value is not None
                setattr(service, key, value)
        db.commit()
        db.refresh(service)
    return service


def delete_service(db: Session, service_id: int):
    service = get_service(db, service_id)
    if service:
        # First delete related barber-service links
        barber_services = db.query(BarberService).filter(BarberService.service_id == service_id).all()
        for barber_service in barber_services:
            db.delete(barber_service)
        
        # Then delete the service
        db.delete(service)
        db.commit()
        return True
    return False
