from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict, computed_field
from typing import List, Optional

from src.app.schemas.barber import BarberOut
from src.app.schemas.service import ServiceOut


class AppointmentCreate(BaseModel):
    name: str
    phone_number: str = Field(..., alias="phoneNumber")
    barber_id: int = Field(..., alias="barberId")
    service_id: int = Field(..., alias="serviceId")
    addon_ids: List[int] = Field(..., alias="addonIds")
    scheduled_time: datetime

    model_config = ConfigDict(populate_by_name=True)

class AppointmentUpdate(BaseModel):
    appointment_id: int
    scheduled_time: datetime
    model_config = ConfigDict(populate_by_name=True)


class AppointmentRead(BaseModel):
    id: int
    name: str
    phone_number: str
    barber_id: int
    service_id: int
    total_duration: int
    total_price: int
    scheduled_time: datetime
    user_id: int

    model_config = ConfigDict(populate_by_name=True)


class AppointmentList(BaseModel):
    id: int
    name: str
    phone_number: str
    barber_id: int
    service_id: int
    total_duration: int
    total_price: int

    model_config = ConfigDict(from_attributes=True)


class AddonsOut(BaseModel):
    id: int
    name: str
    duration: int
    price: int

    model_config = ConfigDict(from_attributes=True)


class AppointmentReadDetailed(BaseModel):
    id: int
    name: str
    phone_number: str
    barber_id: int
    service_id: int
    total_duration: int
    total_price: int
    addons: List[AddonsOut]

    model_config = ConfigDict(from_attributes=True)


class AppointmentResponse(BaseModel):
    id: int
    user_id: int
    name: str
    phone_number: str
    barber_id: int
    service_id: int
    addons: Optional[List[AddonsOut]] = None
    total_duration: int
    total_price: int
    scheduled_time: datetime
    created_at: datetime

    service: ServiceOut
    barber: BarberOut

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def service_name(self) -> str:
        return self.service.name if hasattr(self, 'service') and self.service else "Unknown Service"

    @computed_field
    @property
    def barber_name(self) -> str:
        return self.barber.name if hasattr(self, "barber") and self.barber else "Unknown Barber"

    @computed_field
    @property
    def full_service_title(self) -> str:
        service_name = self. service.name if hasattr(self, "service") and self.service else "Unknown Service"
        addons_name = [addon.name for addon in self.addons] if hasattr(self, "addons") and self.addons else []
        return " + ".join([service_name] + addons_name)


class AppointmentShortUserView(BaseModel):
    id: int
    barber_name: str
    full_service_title: str
    scheduled_day: str
    scheduled_date: str
    scheduled_time: str
    total_price: int


class AppointmentGroupedUserView(BaseModel):
    upcoming: List[AppointmentShortUserView]
    completed: List[AppointmentShortUserView]


