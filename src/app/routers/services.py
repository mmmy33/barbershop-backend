from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.app.auth.dependencies import admin_required, get_current_user
from src.app.database import get_db
from src.app.crud import service as crud
from src.app.models.user import User
from src.app.schemas.service import ServiceCreate, ServiceRead, ServiceBase, ServiceUpdate, ServiceWithBarbersResponse
from typing import List

router = APIRouter(tags=["Services"])


@router.post("/", response_model=ServiceWithBarbersResponse)
def create_service(
        service: ServiceCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(admin_required)
):
    return crud.create_service(db=db, service=service)


@router.get("/", response_model=List[ServiceWithBarbersResponse])
def get_all_services(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = crud.get_services(db=db)

    return crud.get_services(db=db)


@router.put("/{service_id}", response_model=ServiceWithBarbersResponse)
def update_service(
        service_id: int,
        updated_data: ServiceUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(admin_required)
):
    result = crud.update_service(db=db, service_id=service_id, updated_data=updated_data)
    if not result:
        raise HTTPException(status_code=404, detail="Service not found")
    return result


@router.delete("/{service_id}", status_code=204)
def delete_service(
        service_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(admin_required)
):
    if not crud.delete_service(db=db, service_id=service_id):
        raise HTTPException(status_code=404, detail="Service not found")
