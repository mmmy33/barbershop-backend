from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from src.app.schemas.barber import BarberRead


class ServiceBase(BaseModel):
    name: str
    duration: int
    price: int


class ServiceCreate(ServiceBase):
    pass


class ServiceRead(ServiceBase):
    id: int
    barbers: List[BarberRead] = []

    model_config = ConfigDict(from_attributes=True)


class ServiceUpdate(BaseModel):
    name: Optional[str] = None
    duration: Optional[int] = None
    price: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class ServiceOut(BaseModel):
    id: int
    name: str
    # duration: int
    price: int

    model_config = ConfigDict(from_attributes=True)
