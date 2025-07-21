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
        for key, value in updated_data.model_dump().items():
            setattr(service, key, value)
        db.commit()
        db.refresh(service)
    return service


def delete_service(db: Session, service_id: int):
    service = get_service(db, service_id)
    if service:
        db.delete(service)
        db.commit()
        return True
    return False
