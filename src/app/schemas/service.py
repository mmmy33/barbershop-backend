from typing import List, Optional

from pydantic import BaseModel, ConfigDict, model_validator

from src.app.models.service import Service
from src.app.schemas.barber import BarberRead




class ServiceCreate(BaseModel):
    name: str
    price: int

class ServiceBase(BaseModel):
    duration: int


class BarberDurationInfo(BaseModel):
    id: int
    name: str
    duration: int

class BarberServiceResponse(BaseModel):
    service_id: int
    duration: int

class ServiceWithBarbersResponse(BaseModel):
    id: int
    name: str
    price: int
    barbers: List[BarberDurationInfo] = []

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def prepare_data(cls, data):
        if isinstance(data, Service):  # Якщо це SQLAlchemy модель
            return {
                "id": data.id,
                "name": data.name,
                "price": data.price,
                "barbers": [
                    {
                        "id": bs.barber.id,
                        "name": bs.barber.name,
                        "duration": bs.duration
                    }
                    for bs in data.barber_services
                ]
            }
        return data




class ServiceRead(ServiceBase):
    id: int
    barbers: List[BarberRead] = []

    model_config = ConfigDict(from_attributes=True)


class ServiceUpdate(BaseModel):
    name: Optional[str] = None

    price: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class ServiceOut(BaseModel):
    id: int
    name: str
    # duration: int
    price: int

    model_config = ConfigDict(from_attributes=True)
