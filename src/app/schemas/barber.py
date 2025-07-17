from typing import Optional, List

from pydantic import BaseModel, ConfigDict


class BarberBase(BaseModel):
    name: str
    avatar_url: Optional[str] = None


class BarberCreate(BarberBase):
    email: str
    pass


class BarberRead(BarberBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class ServiceAssignment(BaseModel):
    service_id: int
    duration: int  # тривалість у хвилинах

class AssignServices(BaseModel):
    services: List[ServiceAssignment]


class AssignAddons(BaseModel):
    addon_ids: List[int]


class BarberUpdate(BaseModel):
    name: Optional[str] = None
    avatar_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class BarberOut(BaseModel):
    id: int
    name: str
    avatar_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
